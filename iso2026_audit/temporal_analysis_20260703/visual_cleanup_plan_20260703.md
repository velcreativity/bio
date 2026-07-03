# Visual Cleanup Plan — after BLOCKED_VISUAL_REVIEW_FAILED (run_20260703_110920)

Scope: fix the two visual-review failures without losing the 14 verified EP-901-01 values.
No DATE_ROLL or any other expansion until a Hancom review passes.

## Finding classification

| Finding | Origin | Class |
|---|---|---|
| "ISO2025 개발원천 반영 후보: Monitoring/check sheet" visible text | Present in BASE target (June 30 review candidate), inherited by draft | BASELINE_CONTAMINATION — not a Zone-1 defect |
| EP-901-01 long-text wrapping | Introduced by the 14-cell fill | APPLICATOR_DEFECT — flattened multi-line source cells |

## Issue 1 — Baseline contamination: REBASE, do not spot-clean

The base `ISO14001_2025_developed_source_reflected_review_candidate.hwpx` (run_20260630_144518) was
produced by the pre-audit pipeline whose ISO14001 output is now proven to be 4/4 false positives.
The visible marker is that pipeline's own candidate annotation — the same "Monitoring/check sheet"
generic label the contradiction audit flagged. The document is not a trustworthy base; patching one
visible artifact leaves unknown others.

**Decision: retire the June 30 ISO14001 review candidate as a base. Regenerate the draft from the
clean ISO14001 standard template** (`data\document_templates\iso\iso_9001-14001`).

Steps:
1. **Artifact census first** (read-only): regex-sweep all section XMLs of the June 30 candidate for
   marker patterns — `반영 후보`, `개발원천`, `검토필요`, `REVIEW`, `candidate`, `ISO2025` — and
   inventory every hit with location. This documents what the old pipeline actually injected
   (expect ≥4, matching its claimed reflected items). Run the same sweep on the clean template
   (expect 0) to validate the pattern list.
2. Rebuild the target cell inventory against the clean template. The rebuilt map's locators were
   resolved against the contaminated candidate; every WRITE row locator must re-resolve to exactly
   one editable cell on the new base. Re-run map lint. Any locator that fails re-resolution goes to
   DEFER, not force-fit.
3. Re-run Zone-1 apply on the clean base. Expected: 14/14 verified, EP-901-01 rows 4–5 only,
   `<tr>` counts unchanged, BinData 0, and **marker-sweep of the new draft = 0 hits**.

## Issue 2 — Wrapping: preserve source cell paragraph structure

The source EP-901-01 cells are multi-paragraph (one line per item: `환경측면 파악 및 영향평가` /
`소음진동규제법 제2조` / `(소음진동배출시설)` — the `l` prefixes in PDF extraction were line-start
bullets). The applicator flattened them into single runs, producing bad wraps.

Fix in the applicator's cell-fill mode:
1. Copy the source cell's internal paragraph structure (`<hp:p>` per line), not a concatenated string.
2. Do not carry bullet artifacts: strip a leading bullet glyph if present, keep the line break.
3. Add a **wrap-fidelity check** to same-run verification: paragraph count written == paragraph count
   in source cell, for every multi-line WRITE row. Value containment check runs on the concatenation
   (unchanged semantics), so the 14/14 strict proof is preserved.

## Permanent guard additions

- **Marker-leakage scan** becomes a standard post-apply check: FAIL the run if any pipeline marker
  pattern appears in draft text. This prevents baseline contamination from ever reaching Hancom
  review again.
- Record in the run manifest which base file (path + hash) a draft was generated from, so a
  contaminated base can be recalled by hash.

## Order of execution

1. Artifact census (read-only) → report
2. Applicator paragraph-structure fix + wrap-fidelity check → synthetic test on sentinel workspace
3. Clean-base cell inventory + map relint
4. Zone-1 re-apply on clean base (14 rows, same scope — no expansion)
5. Second Hancom visual review (same 5-point checklist + confirm marker text gone)

Constraints unchanged: fill existing cells only, no row append, no apply_reflection to originals,
no NVIDIA/API, no staging of HWPX/PDF/HWP, no final acceptance claim.
