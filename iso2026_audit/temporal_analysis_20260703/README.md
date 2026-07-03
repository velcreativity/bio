# ISO 2023→2025 Temporal Analysis & 2026 Projection Package

Generated 2026-07-03 from a character-level diff of the four dated source PDFs
(환경실적 2023/2025, 품질실적 2023/2024) plus read-only inspection of the ISO14001
procedure PDF and ISO9001 HWPX.

## Files

| File | Purpose |
|---|---|
| `iso_temporal_change_matrix_2023_2025.csv` | 36 fields classified by change class (STATIC / DATE_ROLL / CONTENT_EVOLVED / ORG_CHANGE / RECURRING_FINDING / DEFECT_*) with a deterministic 2026 generation rule per field. **This is the input for the ISO14001 map rebuild.** |
| `iso2026_projection_report.md` | Codex V3-patch reconfirmation, full change taxonomy, ranked highest-probability 2026 issues, and the generation policy that unblocks automation. |
| `품질실적문서_2026_draft.md` | Draft quality performance document 2026. Fields tagged `[AUTO]` / `[CONFIRM]` / `[HUMAN-ONLY]`. |
| `환경실적문서_2026_draft.md` | Draft environmental performance document 2026, same tagging. |

## Usage rules

- WRITE-row source values for the map rebuild must come from the **2025 ENV package**
  (not 2023) and the **2024 QMS package**.
- `[HUMAN-ONLY]` fields (실적, 심사결과, 측정치, 참석자) must never be auto-filled.
- `DEFECT_*` rows carry corrections (식품→제조 residue, stale 위험성평가 date,
  3-year-open 분리수거함 action) that need human confirmation before write.

## Safety status at generation time

No HWPX modified. No apply_reflection.py run. No NVIDIA/API call. No final acceptance claimed.
