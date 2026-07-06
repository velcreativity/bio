# CONTENT FILL DIRECTIVE — layout frozen, fill everything from 2025 sources

Base: the current accepted layout candidate (35-page supplement candidate with
organized orientation/structure). Work on a copy; never the base itself.

## Step 0 — LAYOUT FREEZE BASELINE (before any write)

Snapshot and save as freeze manifest:
- section count + each section's pagePr (size, orientation, margins) — byte-level
- table count per section
- per table: sz (width/height), row count, column count, merge map
- footer paragraph positions

The content pass MUST leave every item above unchanged, with exactly one
exception: declared FORM_DUPLICATE additions (below).

## Step 1 — CONTENT MAP (one map, whole file)

For every form in the candidate, map each fillable cell to its 2025 source value:
- EMS forms  <- 2025_환경실적모음_권위스캔기반_원본형_개발본.hwpx
- QMS forms  <- (주)바이오프렌즈_품질실적모음_2024년.hwpx / 2025 quality sources
- 심사보완    <- 2025_심사보완자료_권위스캔기반_원본형_개발본.hwpx
Rules per row: action WRITE (atomic source value, CONTAINMENT verify) or
DATE_WRITE (EXACT_CELL_MATCH) or DEFER (no source / ambiguous) or HUMAN_ONLY
([HUMAN_INPUT] marker only). Generic labels never count as values. No fabrication:
unreadable/uncertain source -> DEFER, never guessed.

## Step 2 — FORM_DUPLICATE (allowed, declared)

When the 2025 source has MORE RECORDS than the target form holds
(e.g. 환경영향등록부 x2, 직무기술서 x2, 교육결과보고서 x3, 법규점검표 x2):
- duplicate the whole form/table to the following page WITHIN THE SAME SECTION
  (inherits identical pagePr — orientation stays correct by construction)
- refresh numbering/labels; fill the copy from the next source record
- each duplication is a declared FORM_DUPLICATE map row and must be claimed
  in parity delta attribution
- page count may grow ONLY by duplicated pages; growth must equal the number
  of FORM_DUPLICATE rows (explained growth, verified)

## Step 3 — APPLY (Zone-1, batched)

- copy-forward lineage with parent hash (R3)
- cell writes preserve donor paragraph structure (multi-<hp:p> copy for long
  cells) — NEVER adjust column widths/table size to fit text (geometry policy:
  a fill that "needs" a resize is a wrong value or wrong cell)
- batch all forms in one session; do not stop for human review between forms

## Step 4 — VERIFY (all gates, one run)

1. V3 per cell under declared mode (CONTAINMENT / EXACT_CELL_MATCH)
2. FREEZE CHECK: re-snapshot structure; diff vs freeze manifest ==
   exactly the claimed FORM_DUPLICATE additions, nothing else
3. three-way parity with delta attribution (every delta manifest-claimed)
4. marker sweep = 0; BinData = 0; row-append only via FORM_DUPLICATE claims
5. render via hancom_render_hook: page count = 35 + duplicated pages;
   wide pages still single landscape pages; no orphan footers/blank pages
6. layout QA + geometry invariants I1-I4

## Step 5 — ONE consolidated human review packet

Single dashboard covering all filled forms + duplicated pages; single pasteback.
No final acceptance claim; state = HUMAN_VISUAL_REVIEW_READY.

## Hard rules

- table orientation: UNTOUCHED  - table structure (rows/cols/merges/sz): UNTOUCHED
- section pagePr: UNTOUCHED     - only text content + declared duplications change
- originals unmodified; no staging of documents; no API calls
