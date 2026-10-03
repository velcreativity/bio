"""Cloud-side CLI: Claude submits jobs to the local PC and reviews what Codex did.

    python bridge/claude_bridge.py ping --wait
    python bridge/claude_bridge.py codex <project> "<task>" [--kind code|general] --wait
    python bridge/claude_bridge.py review <job_id>             # report + re-audit, for Claude to judge
    python bridge/claude_bridge.py fix <job_id> "<instructions>" [--fixer claude|codex] --wait
    python bridge/claude_bridge.py apply <job_id> [--override "<reason>"] --wait
    python bridge/claude_bridge.py discard <job_id> [--reason "..."]
    python bridge/claude_bridge.py hancom <op> --src a.hwpx [--dst b.hwpx] --wait
    python bridge/claude_bridge.py status [<job_id>]
    python bridge/claude_bridge.py logs [--flagged]            # harvested Codex sessions (all projects)
    python bridge/claude_bridge.py usage [--last N]            # Claude vs Codex token use per job

Uses the current git checkout and branch as the transport (see jobqueue.py).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit  # noqa: E402
import jobqueue as jq  # noqa: E402


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return jq.git(here, "rev-parse", "--show-toplevel").stdout.strip()


def current_branch(repo):
    return jq.git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def submit(repo, branch, job, push=True):
    jq.write_job(repo, "pending", job)
    if push:
        jq.git_sync(repo, branch)
        jq.git_commit_push(repo, branch, [os.path.join(jq.QUEUE_DIR, "pending", job["id"] + ".json")],
                           "bridge: submit %s %s" % (job["type"], job["id"]))
    print("submitted", job["id"], job["type"])
    return job["id"]


def wait(repo, branch, job_id, timeout, interval=20):
    deadline = time.time() + timeout
    while True:
        jq.git_sync(repo, branch)
        state, job = jq.find_job(repo, job_id)
        if state == "done":
            return job
        if time.time() >= deadline:
            print("still %s after %ds" % (state, timeout))
            return None
        time.sleep(interval)


def show(job):
    r = job.get("result", {})
    print(json.dumps({"id": job["id"], "type": job["type"], "status": job.get("status"),
                      "finished_at": job.get("finished_at"), "result": r}, ensure_ascii=False, indent=2))


def cmd_review(repo, job_id):
    state, job = jq.find_job(repo, job_id)
    if state != "done":
        sys.exit("job %s is %s" % (job_id, state))
    rd = os.path.join(repo, "bridge", "reports", job_id)

    def read(name):
        p = os.path.join(rd, name)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    diff = read("diff.patch")
    events = read("events.jsonl")
    rep = audit.audit(events, diff)  # re-run here: never trust the agent-side verdict alone
    r = job.get("result", {})
    print("=== JOB %s  (%s, status=%s, state=%s)" % (job_id, job["type"], job.get("status"), r.get("state")))
    print("task:", (job.get("args", {}).get("prompt") or job.get("args", {}).get("instructions") or "")[:2000])
    print("model:", r.get("model"), r.get("effort"), "| coding:", r.get("coding"), "| fix rounds:", r.get("fix_rounds"))
    print("local review:", json.dumps(r.get("review"), ensure_ascii=False, indent=1))
    print("audit (re-run): %s  findings=%d  commands=%d  paths=%d" % (
        rep["verdict"], len(rep["findings"]), rep["stats"]["commands"], rep["stats"]["changed_paths"]))
    for f in rep["findings"]:
        print("  [%s] %s %s :: %s" % (f["verdict"], f["rule"], f["desc"], f["evidence"]))
    print("changed:", ", ".join(rep["changed_paths"][:50]))
    last = read("codex_last_message.md")
    if last:
        print("--- codex last message ---\n" + last[:4000])
    print("--- diff (%d chars) ---" % len(diff))
    print(diff[:60000])
    print("--- report files:", ", ".join(sorted(os.listdir(rd))) if os.path.isdir(rd) else "(none)")


def cmd_status(repo, job_id=None):
    if job_id:
        state, job = jq.find_job(repo, job_id)
        if not job:
            sys.exit("no such job")
        print("state:", state)
        show(job)
        return
    for state in jq.STATES:
        ids = jq.list_jobs(repo, state)
        print("%s (%d)" % (state, len(ids)))
        for jid in ids[-20:]:
            j = jq.read_job(repo, state, jid)
            r = j.get("result", {})
            extra = " ".join(x for x in (j.get("status"), r.get("state"), r.get("audit_verdict"),
                                         (r.get("review") or {}).get("decision")) if x)
            print("  %s  %-14s %s" % (jid, j["type"], extra))


def cmd_logs(repo, flagged_only):
    idx = os.path.join(repo, "bridge", "codex_logs", "index.jsonl")
    if not os.path.exists(idx):
        print("no harvested Codex sessions yet")
        return
    rows = [json.loads(l) for l in open(idx, encoding="utf-8") if l.strip()]
    latest = {}
    for r in rows:
        latest[r["file"]] = r
    by_cwd = {}
    for r in latest.values():
        by_cwd.setdefault(r.get("cwd") or "(unknown)", []).append(r)
    for cwd, items in sorted(by_cwd.items()):
        verdicts = {v: sum(1 for i in items if i["verdict"] == v) for v in ("PASS", "FLAG", "BLOCK")}
        print("%s  sessions=%d  %s" % (cwd, len(items), verdicts))
        for i in sorted(items, key=lambda x: x["file"]):
            if flagged_only and i["verdict"] == "PASS":
                continue
            print("   %-5s %s  cmds=%s paths=%s  %s" % (i["verdict"], i["file"], i["commands"],
                                                      i["changed_paths"], i["last_message"][:100].replace("\n", " ")))


def _n(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def summarize_usage(jobs):
    """Per-job rows and totals of Claude vs Codex token use. Jobs without result.usage are skipped."""
    rows = []
    tot = dict.fromkeys(("claude_calls", "claude_in", "claude_out", "claude_cache_read", "claude_cost_usd",
                         "codex_in", "codex_out"), 0)
    for job in jobs:
        u = (job.get("result") or {}).get("usage")
        if not isinstance(u, dict):
            continue
        c, x = u.get("claude"), u.get("codex")
        c, x = c if isinstance(c, dict) else {}, x if isinstance(x, dict) else {}
        row = {"id": job.get("id"), "type": job.get("type"),
               "claude_calls": _n(c.get("calls")), "claude_in": _n(c.get("input_tokens")),
               "claude_out": _n(c.get("output_tokens")), "claude_cache_read": _n(c.get("cache_read_input_tokens")),
               "claude_cost_usd": _n(c.get("cost_usd")),
               "codex_in": _n(x.get("input_tokens")), "codex_out": _n(x.get("output_tokens"))}
        rows.append(row)
        for k in tot:
            tot[k] += row[k]
    claude_tok = tot["claude_in"] + tot["claude_out"]
    codex_tok = tot["codex_in"] + tot["codex_out"]
    both = claude_tok + codex_tok
    return {"rows": rows, "totals": tot, "claude_tokens": claude_tok, "codex_tokens": codex_tok,
            "codex_share": codex_tok / both if both else None,
            "claude_share": claude_tok / both if both else None}


def cmd_usage(repo, last=None):
    jobs = []
    for jid in jq.list_jobs(repo, "done"):
        j = jq.read_job(repo, "done", jid)
        if j.get("type") in ("codex.exec", "codex.fix"):
            jobs.append(j)
    s = summarize_usage(jobs)
    rows = s["rows"][-last:] if last else s["rows"]
    if last:
        s = summarize_usage([j for j in jobs if j.get("id") in {r["id"] for r in rows}])
    if not rows:
        print("no jobs with usage data yet")
        return s
    print("%-26s %-11s %6s %10s %10s %10s %9s %10s %10s" % (
        "job", "type", "calls", "cl_in", "cl_out", "cl_cache", "cl_usd", "cx_in", "cx_out"))
    for r in rows:
        print("%-26s %-11s %6d %10d %10d %10d %9.4f %10d %10d" % (
            r["id"], r["type"], r["claude_calls"], r["claude_in"], r["claude_out"], r["claude_cache_read"],
            r["claude_cost_usd"], r["codex_in"], r["codex_out"]))
    t = s["totals"]
    print("%-26s %-11s %6d %10d %10d %10d %9.4f %10d %10d" % (
        "TOTAL (%d jobs)" % len(rows), "", t["claude_calls"], t["claude_in"], t["claude_out"],
        t["claude_cache_read"], t["claude_cost_usd"], t["codex_in"], t["codex_out"]))
    print("tokens (input+output, cache reads excluded): claude=%d codex=%d" % (s["claude_tokens"], s["codex_tokens"]))
    if s["codex_share"] is not None:
        print("share: codex %.1f%%  claude %.1f%%" % (s["codex_share"] * 100, s["claude_share"] * 100))
    print("claude cache reads (separate): %d" % t["claude_cache_read"])
    return s


def main():
    ap = argparse.ArgumentParser(description="Claude -> local PC / Codex bridge")
    ap.add_argument("--no-push", action="store_true", help="write job file only")
    ap.add_argument("--timeout", type=int, default=3600)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def with_wait(p):
        p.add_argument("--wait", action="store_true")
        return p

    with_wait(sub.add_parser("ping"))
    p = with_wait(sub.add_parser("codex"))
    p.add_argument("project")
    p.add_argument("prompt")
    p.add_argument("--kind", choices=["code", "general"])
    p.add_argument("--session-id")
    p = with_wait(sub.add_parser("fix"))
    p.add_argument("job_id")
    p.add_argument("instructions")
    p.add_argument("--fixer", choices=["claude", "codex"])
    p.add_argument("--issue", action="append", default=[])
    p.add_argument("--no-rereview", action="store_true")
    p = with_wait(sub.add_parser("apply"))
    p.add_argument("job_id")
    p.add_argument("--override")
    p = with_wait(sub.add_parser("discard"))
    p.add_argument("job_id")
    p.add_argument("--reason", default="")
    p = with_wait(sub.add_parser("hancom"))
    p.add_argument("op", choices=["page_count", "roundtrip", "convert", "export_pdf", "extract_text", "insert_file"])
    p.add_argument("--src")
    p.add_argument("--dst")
    p.add_argument("--target")
    p.add_argument("--donor")
    p = with_wait(sub.add_parser("submit"))
    p.add_argument("type")
    p.add_argument("args_json")
    with_wait(sub.add_parser("harvest"))
    p = sub.add_parser("wait")
    p.add_argument("job_id")
    p = sub.add_parser("review")
    p.add_argument("job_id")
    p = sub.add_parser("status")
    p.add_argument("job_id", nargs="?")
    p = sub.add_parser("logs")
    p.add_argument("--flagged", action="store_true")
    p = sub.add_parser("usage")
    p.add_argument("--last", type=int)
    a = ap.parse_args()

    repo = repo_root()
    branch = current_branch(repo)
    if a.cmd == "review":
        return cmd_review(repo, a.job_id)
    if a.cmd == "status":
        return cmd_status(repo, a.job_id)
    if a.cmd == "logs":
        return cmd_logs(repo, a.flagged)
    if a.cmd == "usage":
        cmd_usage(repo, a.last)
        return
    if a.cmd == "wait":
        job = wait(repo, branch, a.job_id, a.timeout)
        return show(job) if job else sys.exit(1)

    if a.cmd == "ping":
        job = jq.make_job("ping", {}, 300)
    elif a.cmd == "codex":
        args = {"project": a.project, "prompt": a.prompt}
        if a.kind:
            args["kind"] = a.kind
        if a.session_id:
            args["session_id"] = a.session_id
        job = jq.make_job("codex.exec", args, a.timeout)
    elif a.cmd == "fix":
        args = {"job_id": a.job_id, "instructions": a.instructions, "issues": a.issue,
                "rereview": not a.no_rereview}
        if a.fixer:
            args["fixer"] = a.fixer
        job = jq.make_job("codex.fix", args, a.timeout)
    elif a.cmd == "apply":
        job = jq.make_job("codex.apply", {"job_id": a.job_id, "override_reason": a.override}, 600)
    elif a.cmd == "discard":
        job = jq.make_job("codex.discard", {"job_id": a.job_id, "reason": a.reason}, 600)
    elif a.cmd == "hancom":
        args = {k: v for k, v in (("src", a.src), ("dst", a.dst), ("target", a.target), ("donor", a.donor)) if v}
        if a.op == "insert_file":
            args.setdefault("src", args.get("target"))
        job = jq.make_job("hancom." + a.op, args, 900)
    elif a.cmd == "harvest":
        job = jq.make_job("codex.harvest", {}, 900)
    else:
        job = jq.make_job(a.type, json.loads(a.args_json), a.timeout)

    jid = submit(repo, branch, job, push=not a.no_push)
    if getattr(a, "wait", False):
        done = wait(repo, branch, jid, a.timeout)
        if done:
            show(done)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
