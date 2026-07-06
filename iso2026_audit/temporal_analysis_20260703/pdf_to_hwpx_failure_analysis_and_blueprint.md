# PDF -> HWPX Reconstruction: Failure Root Causes and Automation Blueprint

Context: 2025 supplement reconstruction (image-based -> editable HWPX).
Candidate produced via Hancom clipboard: 39 pages vs expected 35.

## Unifying root cause

A faithful HWPX page = 4 inseparable parts:
  (1) content subtree (paragraphs/tables)
  (2) style closure (header.xml IDs: charPr/paraPr/borderFill/fontface refs)
  (3) section geometry (pagePr: orientation, margins, size)
  (4) page-furniture binding (footers, breaks)

Every failed route moved only a subset:

| Route | Moved | Dropped | Observed failure |
|---|---|---|---|
| Raw XML reconstruction | (1) | (2)(3)(4) + package linkage | Hancom reject / bad render (dangling IDRefs) |
| Block-save fragments | (1) partial | package context | fragments cannot reopen |
| XML form fragments | (1) | (2) needs full ID remap | cannot insert reliably |
| COM page deletion | n/a | COM hygiene missing | hangs, orphan Hwp.exe |
| Clipboard transfer | (1)(2) | (3)(4) | 35->39 pages: landscape tables split in portrait sections, orphan footers, blank page |

Measured evidence (candidate XML): 현황표 tables w=68875/68592 HWPU (landscape design)
in portrait sections with usable width 53860; footers as body paragraphs after
h=65027/64541 tables; 2+2 trailing empty paragraphs.

Systemic failure: page count verified once at end of build; geometry errors
from 5 insertions accumulated invisibly. Layout needs same-run per-block
verification, like cells already have.

## Automation blueprint

1. PAGE CENSUS: source-PDF page -> donor doc + donor page + orientation + margins (CSV).
2. DONOR EXTRACTION at whole-package level: copy entire donor HWPX (style closure
   intact by construction); trim pages via COM backwards-deletion under hygiene
   runbook, or XML paragraph-trim + Hancom open/SaveAs normalize.
3. ASSEMBLY via InsertFile with keep-section (never clipboard): each page arrives
   with its own pagePr -> orientation/margins preserved automatically.
4. PER-BLOCK VERIFICATION: after each insert -> page count via COM, render new pages
   (hancom_render_hook), pixel-compare vs supplement PDF page. Fail fast per block.
5. FORMAT-PARITY GUARD: per section pagePr == donor pagePr; per table sz == donor sz;
   tolerance zero. Gate before human review.
6. COM HYGIENE RUNBOOK: single instance; RegisterModule security DLL;
   SetMessageBoxMode auto-answer; watchdog kill+retry-once; stale-process sweep
   before start; copies only; explicit Quit.
7. CONTENT FILL LAST: values go through existing Zone-1 map/apply/V3 chain only
   after geometry passes. Geometry first, content second, never interleaved.

## Immediate repair of current 39-page candidate (no rebuild)

1. Delete trailing empty paragraphs (sections 2,3) -> removes blank page.
2. Split the two 현황표 tables into their own landscape section
   (pagePr width=84188 height=59528, donor margins) -> removes 2-3 spillover pages.
3. Rebind orphan footers (keep-with-previous or trim table height ~1000 HWPU
   where within 1000 of usable height) -> removes footer-only page(s).
4. Re-render via hook -> expect 35 pages -> pixel-parity vs supplement PDF p11+.
5. Run format-parity guard as acceptance evidence.
