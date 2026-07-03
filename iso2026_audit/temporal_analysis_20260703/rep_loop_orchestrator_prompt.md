# Rep Loop Orchestrator Prompt (for codex / Claude session)

Run autonomous learning reps of the HWPX reflection pipeline until the token budget
reserve is reached. Guards are the judge; the goal is coverage of situations and
strategies, not repetition.

## Loop protocol (repeat until harness says SHUTDOWN)

1. `python rep_loop_harness.py next-rep`
   - If `SHUTDOWN`: write RESUME.md summarizing bandit stats, top lessons, and the
     3 next-recommended reps; stop cleanly.
   - If `STAGE_PROMOTED`: announce and continue.
2. Read the rep spec: form, strategy, situation, workspace, playbook_hint.
   READ THE PLAYBOOK HINT FIRST — do not repeat recorded failures.
3. Execute the rep inside `workspace` ONLY:
   - copy clean template in; build the map per the declared strategy;
   - apply with a narrow pass script (reuse existing patterns);
   - run the full guard stack (verify, row-append, marker sweep, BinData,
     three-way parity with delta attribution, layout QA; render hook if available);
   - for FAULT_ situations: plant the defect, expect a guard to hard-block.
4. Collect guard outputs into `guard.json` with fields:
   written_verified, written_total, unexpected_changed_cells, row_append_detected,
   marker_hits, bindata_changes, parity_unclaimed_deltas, layout_high_risk,
   guard_blocked, deferred_correctly.
5. `python rep_loop_harness.py record --guard-json guard.json
      --lesson "<one honest sentence>" --root-cause "<if failed>" --tokens <estimate>`
6. Every 5 reps: `status`; if win_rate > 0.9 across 20+ reps in current stage,
   expect stage promotion soon — prefer unexplored combos.

## Hard rules

- Never touch paths listed in forbidden_paths. Never write to real lineage chains.
- Never claim a human-gate outcome. All reps are SIMULATION.
- A GUARD_MISSED_FAULT result is the most valuable outcome of the entire loop:
  stop the loop, write the guard fix proposal, and surface it before continuing.
- Lessons must be honest and specific ("label anchor failed because 작성일 appears
  twice in EP-603-02; disambiguate by table index"), never generic ("worked fine").
- Do not stage/commit HWPX. Commit harness/state only when asked.

## Why this converges

- UCB bandit spends tokens on weak (form x strategy x situation) combos and retires
  mastered ones (3-pass streak) — no wasted repetition.
- Fault-injection reps give the guard stack adversarial regression coverage.
- lessons.jsonl accumulates supervised exemplars: (scenario, approach, guard verdict,
  human-readable lesson) — the training corpus for the future automation model.
- playbook.md is the distilled policy: next session starts from knowledge, not zero.
