# Project History Review — Errors, Rules, Suggestions, Subagent Architecture

Reviewed: PROJECT_FULL_HISTORY_20260703.txt (2,225 lines). Date: 2026-07-03.

## A. Errors / gaps found

| # | Finding | Evidence in history | Consequence if unfixed |
|---|---|---|---|
| E1 | Rule 14 ("no row append") contradicts EP-601-03 form-duplication practice; FORM_DUPLICATE is not a declared action class | Phase 10 duplication pass vs §2 rule 14, Phase 6 "no structural row append in v1" | Next agent wrongly blocks duplication or wrongly allows undeclared structural change; page-flow QA false-fails duplication passes |
| E2 | Two meanings of "verified": V3 strict predicate rejects bare dates (`is_bare_temporal_or_numeric`), but DATE_ROLL / deferred-locator passes self-verified date cells | §16.5 predicate vs Phase 9/10 date writes | Re-running canonical V3 over the current draft contradicts pass manifests — same contradiction class as the ISO14001 "4 verified" incident |
| E3 | Normalization is NFC-only; full-width Latin/digits (２０２５) are not folded | §16.5 `normalize_for_cell_proof` | Latent false negatives (`VALUE_NOT_IN_TARGET_CELL` on visually identical text) |
| E4 | Previously verified EP-901-01 cells were rewritten ("alignment refresh") with no supersession of the earlier verification records | Phase 10, 46-cell pass | Audit trail holds two conflicting verification records per cell with no "current" pointer |
| E5 | Draft lineage is informal ("copy latest draft forward"); no parent-hash chain; two parallel chains (2025/2026) plus retired bases coexist | §6 lists 9 draft/base paths; §16.4 flow | One wrong parent pick silently forks the lineage |
| E6 | 46-cell pass mixed five concerns (gap audit + label verify + emergency check + EP-901-02 apply + alignment rewrite), violating the narrow-pass principle; 46 cells in one human review | Phase 10 | Human review reliability collapses at that size (marker census: humans caught 1 of 93) |
| E7 | No .gitignore/pre-commit protection for binary docs; raw HWPX untracked in repo; acceptance-chain tools (layout_style_qa.py, gap-audit script) uncommitted | §5, §11.3–4, §16.15 | One `git add -A` from committing documents; repeat of the pre-bcbbfa0 unversioned-verifier risk |
| E8 | Human gate decisions recorded in chat, not decision files ("user later said all pass") | Phase 9 | state_tracker promotions rest on non-durable evidence |
| E9 | Date format policy open (yy.mm.dd vs long form) while passes keep writing dates ad hoc | §10.5 | Inconsistency bakes deeper with every pass |
| E10 | Pasted API keys marked compromised but never rotated | Phase 8, §11.5 | Live compromised credential |
| E11 | Layout QA gate existed but did not gate the 46-cell apply (sentinel-validated only) | Phase 10 vs Phase 11 | Biggest wrapping-risk pass shipped without the wrapping gate |

## B. RULES (adopt into .ai/RULES.md and map lint — mandatory)

1. **R1 Declared action classes.** Add `FORM_DUPLICATE` (guards: template integrity, numbering refresh, expected-page-shift exemption in page-flow QA) and `DATE_WRITE`. Amend rule 14 to "no *undeclared* structural change."
2. **R2 Two verification modes, both V3-executable.** `CONTAINMENT` (atomic values) and `EXACT_CELL_MATCH` (dates/short numerics). Every written cell must be re-verifiable by canonical V3 under its declared mode; pass-local verify is never the sole proof.
3. **R3 Chained draft lineage.** Manifest records parent draft SHA256 + run id; apply scripts refuse a base that is not the registered chain head. 2025 and 2026 chains are separate registries.
4. **R4 Rewrite supersession.** Rewriting a verified cell requires action `REWRITE`, re-verification, and marking prior records superseded.
5. **R5 Decision files.** No state_tracker promotion without a pasteback decision file in the run folder. Chat approval is void.
6. **R6 Mechanical git protection.** .gitignore for `*.hwp *.hwpx *.pdf *.doc* *.xls* *.zip` + pre-commit hook blocking them.
7. **R7 Committed tools only.** Tools that gate acceptance must be committed with regression fixtures before output is trusted (V3 precedent → layout_style_qa.py, gap-audit script now).
8. **R8 Layout QA in-run.** Every apply pass runs layout QA against the real draft in the same run.
9. **R9 Format verbatim.** Per-field format recorded in the map; 2025 values verbatim from source; no silent format normalization.
10. **R10 Rotate exposed NVIDIA keys**; scan git history for key strings.
11. **R11 Review-size cap.** One form or ≤ ~20 cells per human review pass.
12. **R12 Normalization spec.** NFKC (or NFC + explicit width folding), fixtures including full-width digits, documented per run.

## C. SUGGESTIONS (recommended, not gate-blocking)

- S1 Machine-readable run registry: `runs_index.csv` (run path, script, chain, parent hash, result, human-gate status).
- S2 Extract shared `hwpx_lib` from duplicated helpers **after** remaining ISO14001 2025 gaps complete.
- S3 UTF-8 console policy in .ps1 wrappers (`chcp 65001`, `PYTHONIOENCODING=utf-8`); clean mojibake labels in layout QA.
- S4 Sibling .txt pasteback next to every HTML checklist.
- S5 Log every pass as a structured exemplar (see D) — this becomes model training data.

## D. Subagent architecture toward the automation AI model

Core lesson from the project's own history: the ISO14001 false positives were caught by
**disagreement between independent checkers** (map enrichment vs V3), not by one checker
improving. Subagents institutionalize that independence.

| Role | Agent type | Contract |
|---|---|---|
| Source inventory | Explore (read-only) | Reads source HWPX/PDF → value inventory with exact citations. Never sees target. |
| Map builder | general-purpose | Change matrix + inventories → reflection_map rows. Builds map, never applies. |
| Applier | general-purpose, worktree isolation | Runs one narrow pass in a draft workspace. Writes only in draft dirs. |
| Blind verifier | fresh session | Gets ONLY draft + map (not applier logs/expected outputs); re-verifies from raw XML. |
| Adversarial auditor | general-purpose | Routine marker/fabrication/generic-label/lineage hunts — contradiction audit as a habit, not a post-mortem. |
| Pass designer | Plan agent | Designs locators/action classes/guards before code exists. |
| Script reviewer | code-review + verify skills | Gates every new pass script before commit (R7). |

Binding subagent rules:
- No writes outside draft dirs; no subagent records a human-gate outcome.
- All exchange via run-folder artifacts; the orchestrator (main session) owns state/sequencing.
- Builder and verifier are never the same context (self-verification is the pre-patch-V3 failure mode).

Path to the automation model: each pass yields a training row —
`(source citation, map row, written cell, blind-verifier verdict, human verdict)`.
Human corrections are gold labels. Accumulated, this dataset lets a model *propose* maps for
new forms, with the guard chain demoted from constant error-catcher to spot-check gate.
Guards never come off; they stop being the bottleneck.
