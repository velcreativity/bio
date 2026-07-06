# Table Geometry Change Policy — when automation may alter table size/shape

Core principle: FIX THE CONTAINER FIRST, TOUCH THE TABLE LAST, NEVER CHANGE STRUCTURE.
Source-native table dimensions are the fidelity TARGET, not an adjustable knob.

## Mandatory diagnostic before any layout edit (no exceptions)

Measure four numbers; they select the branch mechanically:
  A = table width/height (tbl sz in draft)
  B = section usable width/height (pagePr size - margins)
  C = donor/source table width/height (reference truth)
  D = footer/separator position vs page bottom

## Decision ladder

| Condition | Diagnosis | Action | Table size change |
|---|---|---|---|
| A==C and A>B (width) | right table, wrong frame | change SECTION orientation/margins to source-native | NO |
| A==C, fits, bad wrapping | flattened cell paragraphs | rebuild multi-<hp:p> from donor | NO |
| A!=C | drifted from source | restore A to C (repair toward reference) | toward C only |
| A==C, fits width, height within ~1000 HWPU of B | exact-fit footer orphan | rebind footer; else trim height <=1000 HWPU, logged | bounded, last resort |
| no donor | geometry from scan | grid-extractor measurement + convergence loop (±2px) | measurement-driven only |
| none resolves | unknown | NEEDS_HUMAN_REVIEW with all four numbers; STOP iterating | NO |

## Forbidden

1. Scaling a table to fit wrong orientation (destroys fidelity to "solve" spillover).
2. Column-width changes to fix wrapping (wrapping = paragraph structure problem).
3. Row/column/merge changes for layout (structure = FORM_DUPLICATE declaration only).
4. Rotating the table object.
5. Two geometry edits in one iteration. One edit -> re-render -> re-measure, always.

## Guard invariants (add to format-parity guard)

I1: table_width <= section_usable_width   (violation => section fix, never resize)
I2: table_dims == donor_dims, tolerance 0 (when donor exists)
I3: any size delta manifest-claimed with reason code:
    RESTORE_TO_SOURCE | FOOTER_ORPHAN_TRIM<=1000 | NO_DONOR_CONVERGENCE
I4: footer paragraph in same section as its table

A size change without a reason code FAILS the run.

## Iteration protocol (fixes the thrashing)

1. Measure A/B/C/D. 2. Pick ONE branch from the ladder. 3. Make ONE edit.
4. Re-render via hancom_render_hook. 5. Re-measure. 6. Converged? stop : goto 1.
Max 3 iterations per table; then NEEDS_HUMAN_REVIEW with the measurement history.
