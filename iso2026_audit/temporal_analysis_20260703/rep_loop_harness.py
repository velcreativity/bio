#!/usr/bin/env python3
"""
rep_loop_harness.py — autonomous rep loop for HWPX reflection learning.

The model (codex / Claude) calls this harness once per rep:
  1. next-rep     -> harness picks scenario via UCB bandit, prints rep spec
  2. (model plans and executes the rep: builds map, runs apply in REP_WORKSPACE,
     runs the guard stack via existing tools)
  3. record       -> harness scores the rep from guard outputs, appends exemplar,
                     updates bandit stats, updates playbook, checkpoints
  4. status       -> budget/curriculum state; tells the model to continue or shut down

Design principles:
  - Guards are the judge. A rep's score comes ONLY from guard tool outputs
    (verify manifest, parity attribution, marker sweep, row-append, layout QA).
  - Fault-injection reps invert scoring: the rep passes only if the guard FAILS.
  - Everything persists in JSON/JSONL so a new session resumes mid-curriculum.
  - The harness NEVER writes HWPX itself; it selects, scores, and remembers.
    The model + existing narrow pass scripts do the document work.

Safety rails:
  - Refuses to run if REP_WORKSPACE overlaps any registered lineage path.
  - Every rep spec carries simulation=True and forbidden_paths.
  - No rep may set or imply a human-gate outcome.
"""

from __future__ import annotations
import argparse, json, math, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration — adjust paths for the local machine.
# --------------------------------------------------------------------------
STATE_DIR = Path(os.environ.get("REP_STATE_DIR", r"C:\ISO2026_AUDIT\rep_loop\state"))
REP_WORKSPACE = Path(os.environ.get("REP_WORKSPACE", r"C:\ISO2026_AUDIT\rep_loop\REP_WORKSPACE"))
# Real lineage roots the harness must never let a rep touch:
FORBIDDEN_PATHS = [
    r"C:\ISO2026_AUDIT\reflection_pipeline_v1_iso2025",
    r"C:\ISO2026_AUDIT\reflection_pipeline_v1_iso14001",
    r"C:\Users\BIOFRIENDS AI\Documents\biofriends-ai-platform\data",
]
TOKEN_BUDGET_DEFAULT = 400_000          # approx tokens for the whole session loop
SHUTDOWN_RESERVE_FRACTION = 0.10        # reserve for checkpoint + RESUME.md
MASTERY_STREAK = 3                      # consecutive passes to retire a combo

# --------------------------------------------------------------------------
# Scenario matrix (three axes). Extend freely; bandit handles the growth.
# --------------------------------------------------------------------------
FORMS = [
    "EP-602-01_legal_register",
    "EP-602-02_legal_checklist_x2",
    "EP-601-01_aspect_identification",
    "EP-603-01_annual_goals",
    "EP-603-02_action_plan",
    "EP-603-03_job_description_x2",
    "EDU_result_reports_x3",
    "EP-805-01_emergency_report_body",
    "QP-401_issue_tables",            # ISO9001 transfer stage
    "FULL_DOC_ISO14001",              # stage D end-to-end
]
STRATEGIES = [
    "label_anchor_locator",     # find row/col by neighbor label text
    "index_locator",            # fixed table/row/cell indices
    "donor_copy_structure",     # copy_cell_structure from source cell
    "set_text_simple",          # set_cell_text for short atomic values
    "split_multi_pass",         # one form across 2+ narrow passes
    "single_generalized_pass",  # one generalized map-runner pass
]
SITUATIONS = [
    "clean_base",
    "multi_record_duplication",     # FORM_DUPLICATE action class
    "fullwidth_chars_in_source",    # NFKC normalization stress
    "long_multiparagraph_cells",    # wrap-fidelity stress
    "placeholder_replacement",      # '년 월 일' -> value
    "source_missing_must_defer",    # correct answer is DEFER, not write
    # fault-injection situations: rep PASSES only if guard FAILS
    "FAULT_marker_text_planted",
    "FAULT_row_appended_undeclared",
    "FAULT_wrong_cell_write",
    "FAULT_generic_label_as_value",
    "FAULT_bindata_touched",
]

def is_fault(situation: str) -> bool:
    return situation.startswith("FAULT_")

# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
def _load(name: str, default):
    p = STATE_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default

def _save(name: str, obj) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _append_jsonl(name: str, obj) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# --------------------------------------------------------------------------
# Bandit (UCB1 over form x strategy x situation combos)
# --------------------------------------------------------------------------
def combo_key(form: str, strategy: str, situation: str) -> str:
    return f"{form}||{strategy}||{situation}"

def pick_scenario(stats: dict, stage: str) -> dict:
    """UCB1 selection restricted to the current curriculum stage."""
    stage_forms = {
        "A": [f for f in FORMS if not f.startswith(("QP-", "FULL_"))],
        "B": [f for f in FORMS if not f.startswith(("QP-", "FULL_"))],
        "C": [f for f in FORMS if not f.startswith("QP-")],
        "D": FORMS,
        "E": FORMS,
    }[stage]
    stage_situations = {
        "A": [s for s in SITUATIONS if not is_fault(s)],
        "B": SITUATIONS,                      # faults unlocked
        "C": SITUATIONS,
        "D": [s for s in SITUATIONS if not is_fault(s)] + ["FAULT_marker_text_planted"],
        "E": SITUATIONS,
    }[stage]

    total = sum(v["n"] for v in stats.values()) or 1
    best, best_score = None, -1.0
    for form in stage_forms:
        for strat in STRATEGIES:
            for sit in stage_situations:
                key = combo_key(form, strat, sit)
                s = stats.get(key, {"n": 0, "wins": 0, "streak": 0})
                if s["streak"] >= MASTERY_STREAK:
                    continue                    # mastered; don't waste tokens
                if s["n"] == 0:
                    ucb = 10.0 + random.random() # explore unseen combos first
                else:
                    ucb = s["wins"] / s["n"] * -1 + 1 \
                        + math.sqrt(2 * math.log(total) / s["n"])
                    # note: failing combos rank HIGHER (1 - winrate) — we spend
                    # tokens where the pipeline is weak, not where it is strong
                if ucb > best_score:
                    best_score, best = ucb, (form, strat, sit)
    if best is None:
        return {}                               # everything mastered this stage
    form, strat, sit = best
    return {"form": form, "strategy": strat, "situation": sit}

# --------------------------------------------------------------------------
# Scoring — from guard outputs only
# --------------------------------------------------------------------------
GUARD_FIELDS = [
    # the model fills these from actual guard tool outputs after the rep
    "written_verified", "written_total",
    "unexpected_changed_cells", "row_append_detected",
    "marker_hits", "bindata_changes",
    "parity_unclaimed_deltas", "layout_high_risk",
    "guard_blocked",            # True if any guard hard-blocked the rep
    "deferred_correctly",       # for source_missing_must_defer situations
]

def score_rep(spec: dict, guard: dict) -> dict:
    fault = is_fault(spec["situation"])
    clean = (
        guard.get("unexpected_changed_cells", 1) == 0
        and not guard.get("row_append_detected", True)
        and guard.get("marker_hits", 1) == 0
        and guard.get("bindata_changes", 1) == 0
        and guard.get("parity_unclaimed_deltas", 1) == 0
        and guard.get("layout_high_risk", 1) == 0
    )
    if fault:
        # fault reps pass only if the guard stack CAUGHT the planted defect
        passed = bool(guard.get("guard_blocked", False))
        kind = "GUARD_CAUGHT_FAULT" if passed else "GUARD_MISSED_FAULT"
    elif spec["situation"] == "source_missing_must_defer":
        passed = bool(guard.get("deferred_correctly", False)) and clean
        kind = "CORRECT_DEFER" if passed else "WRONG_WRITE_OR_DIRTY"
    else:
        wv, wt = guard.get("written_verified", 0), guard.get("written_total", 0)
        passed = clean and wt > 0 and wv == wt
        kind = "VERIFIED_CLEAN" if passed else "FAILED_OR_DIRTY"
    return {"passed": passed, "kind": kind}

# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_next_rep(args):
    _safety_check()
    stats = _load("bandit_stats.json", {})
    meta = _load("loop_meta.json", _fresh_meta(args))
    if _budget_exhausted(meta):
        print(json.dumps({"action": "SHUTDOWN", "reason": "token budget reserve reached",
                          "write": "RESUME.md then stop"}, ensure_ascii=False))
        return
    spec = pick_scenario(stats, meta["stage"])
    if not spec:
        meta["stage"] = _next_stage(meta["stage"])
        _save("loop_meta.json", meta)
        print(json.dumps({"action": "STAGE_PROMOTED", "new_stage": meta["stage"]},
                         ensure_ascii=False))
        return
    rep_id = f"rep_{meta['rep_counter']:04d}"
    spec.update({
        "rep_id": rep_id,
        "simulation": True,
        "workspace": str(REP_WORKSPACE / rep_id),
        "forbidden_paths": FORBIDDEN_PATHS,
        "stage": meta["stage"],
        "instructions": _rep_instructions(spec),
        "playbook_hint": _playbook_lookup(spec["form"]),
    })
    meta["rep_counter"] += 1
    meta["open_rep"] = spec
    _save("loop_meta.json", meta)
    print(json.dumps(spec, ensure_ascii=False, indent=2))

def cmd_record(args):
    guard = json.loads(Path(args.guard_json).read_text(encoding="utf-8")) \
        if args.guard_json else json.loads(sys.stdin.read())
    meta = _load("loop_meta.json", None)
    if not meta or not meta.get("open_rep"):
        sys.exit("no open rep to record")
    spec = meta["open_rep"]
    verdict = score_rep(spec, guard)
    stats = _load("bandit_stats.json", {})
    key = combo_key(spec["form"], spec["strategy"], spec["situation"])
    s = stats.setdefault(key, {"n": 0, "wins": 0, "streak": 0})
    s["n"] += 1
    if verdict["passed"]:
        s["wins"] += 1; s["streak"] += 1
    else:
        s["streak"] = 0
    _save("bandit_stats.json", stats)
    exemplar = {
        "rep_id": spec["rep_id"], "ts": datetime.now(timezone.utc).isoformat(),
        "form": spec["form"], "strategy": spec["strategy"],
        "situation": spec["situation"], "stage": spec["stage"],
        "guard": guard, "verdict": verdict,
        "lesson": args.lesson or "",
        "root_cause": args.root_cause or "",
    }
    _append_jsonl("lessons.jsonl", exemplar)
    if args.lesson:
        _playbook_update(spec["form"], spec["strategy"], verdict, args.lesson)
    meta["open_rep"] = None
    meta["tokens_spent_estimate"] += int(args.tokens or meta["tokens_per_rep_estimate"])
    n = sum(v["n"] for v in stats.values())
    meta["tokens_per_rep_estimate"] = max(
        1000, meta["tokens_spent_estimate"] // max(1, n))
    _save("loop_meta.json", meta)
    print(json.dumps({"recorded": spec["rep_id"], "verdict": verdict,
                      "combo_stats": s,
                      "budget_left": meta["token_budget"] - meta["tokens_spent_estimate"]},
                     ensure_ascii=False))

def cmd_status(args):
    meta = _load("loop_meta.json", None)
    stats = _load("bandit_stats.json", {})
    if not meta:
        print(json.dumps({"state": "FRESH", "hint": "run next-rep to start"})); return
    total = sum(v["n"] for v in stats.values())
    wins = sum(v["wins"] for v in stats.values())
    mastered = sum(1 for v in stats.values() if v["streak"] >= MASTERY_STREAK)
    print(json.dumps({
        "stage": meta["stage"], "reps_done": total, "wins": wins,
        "win_rate": round(wins / total, 3) if total else None,
        "mastered_combos": mastered,
        "budget_left_estimate": meta["token_budget"] - meta["tokens_spent_estimate"],
        "shutdown_at": int(meta["token_budget"] * (1 - SHUTDOWN_RESERVE_FRACTION)),
        "open_rep": meta.get("open_rep") and meta["open_rep"]["rep_id"],
    }, ensure_ascii=False, indent=2))

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _fresh_meta(args):
    return {"stage": "A", "rep_counter": 1, "open_rep": None,
            "token_budget": int(getattr(args, "budget", 0) or TOKEN_BUDGET_DEFAULT),
            "tokens_spent_estimate": 0, "tokens_per_rep_estimate": 8000}

def _budget_exhausted(meta) -> bool:
    limit = meta["token_budget"] * (1 - SHUTDOWN_RESERVE_FRACTION)
    return meta["tokens_spent_estimate"] + meta["tokens_per_rep_estimate"] > limit

def _next_stage(stage: str) -> str:
    order = "ABCDE"
    i = order.index(stage)
    return order[min(i + 1, len(order) - 1)]

def _safety_check():
    ws = str(REP_WORKSPACE).lower()
    for p in FORBIDDEN_PATHS:
        if ws.startswith(p.lower()) or p.lower().startswith(ws):
            sys.exit(f"SAFETY: REP_WORKSPACE overlaps forbidden path {p}")

def _rep_instructions(spec) -> list[str]:
    base = [
        "Copy clean template into the rep workspace; never touch real lineage paths.",
        "Build a narrow map for this form using the declared strategy.",
        "Apply, then run the FULL guard stack: verify manifest, row-append check, "
        "marker sweep, BinData check, three-way parity with delta attribution, layout QA.",
        "Collect guard outputs into guard.json and call `record`.",
        "Write one honest lesson: what worked, what failed, why.",
    ]
    if is_fault(spec["situation"]):
        base.insert(2, "Plant the specified defect AFTER apply; the rep passes only if "
                       "a guard hard-blocks. If guards stay green, record GUARD_MISSED_FAULT "
                       "and propose the guard fix in the lesson.")
    if spec["situation"] == "source_missing_must_defer":
        base.insert(1, "Correct behavior is DEFER with zero writes. Writing anything fails the rep.")
    return base

def _playbook_lookup(form: str) -> str:
    p = STATE_DIR / "playbook.md"
    if not p.exists():
        return ""
    lines, keep, out = p.read_text(encoding="utf-8").splitlines(), False, []
    for ln in lines:
        if ln.startswith("## "):
            keep = form in ln
        if keep:
            out.append(ln)
    return "\n".join(out[:40])

def _playbook_update(form: str, strategy: str, verdict: dict, lesson: str):
    p = STATE_DIR / "playbook.md"
    entry = f"- [{'PASS' if verdict['passed'] else 'FAIL'}/{strategy}] {lesson}\n"
    if p.exists() and f"## {form}" in p.read_text(encoding="utf-8"):
        text = p.read_text(encoding="utf-8")
        idx = text.index(f"## {form}") + len(f"## {form}") + 1
        p.write_text(text[:idx] + entry + text[idx:], encoding="utf-8")
    else:
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n## {form}\n{entry}")

# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next-rep");  n.add_argument("--budget", type=int, default=0)
    r = sub.add_parser("record")
    r.add_argument("--guard-json"); r.add_argument("--lesson", default="")
    r.add_argument("--root-cause", default=""); r.add_argument("--tokens", type=int, default=0)
    sub.add_parser("status")
    args = ap.parse_args()
    {"next-rep": cmd_next_rep, "record": cmd_record, "status": cmd_status}[args.cmd](args)

if __name__ == "__main__":
    main()
