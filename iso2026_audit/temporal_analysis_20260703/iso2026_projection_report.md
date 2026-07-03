# ISO 2026 Projection Report — Temporal Analysis 2023→2025 and 2026 Predicted Issues

Status: DIAGNOSTIC + DRAFT PLANNING. No HWPX modified. No apply_reflection run. No API calls.
Sources: ENV package 2023 (20p), ENV package 2025 (20p), QMS package 2023 (33p), QMS package 2024 (34p),
ISO14001 procedure set PDF (77p, blank templates), ISO9001 HWPX (filled QP-401 body + blank forms).

---

## Part 1 — Reconfirmation of the codex V3 verifier patch

The reported post-patch numbers are **consistent with the ground-truth documents**:

| Claim | Ground truth check | Verdict |
|---|---|---|
| ISO14001 verified = 0 | Target HWPX record forms are blank templates (모니터링 Check Sheet, 현황표 all header-only) | CONFIRMED CORRECT |
| ISO9001 verified = 6 (was 13) | Target HWPX has genuinely filled QP-401 issue/stakeholder tables (19 filled impact rows) — nonzero is expected, so the verifier was not overcorrected | PLAUSIBLE, needs row list |
| Generic-as-value = 1 | "Monitoring/check sheet" is the literal title of source form EP-901-02 | CONFIRMED CORRECT |
| Readiness = BLOCKED_TRACEABILITY_INCOMPLETE | Correct: writing works (Zone-1 sentinel PASS); proof chain is the blocker | CONFIRMED |

**Open verification gaps in the codex patch (request these before trusting it fully):**

1. **Transition accounting.** ISO9001 went 13 → 6 verified. 6 verified + 3 register-only + 1 generic = 10; **3 rows are unaccounted for.** Require a per-row transition table (old status → new status → reason) for all 13.
2. **The surviving 6 need a spot-check** against the filled QP-401 tables (외부/내부 이슈, 이해관계자 Needs). Each must show: exact locator + full cell text + contained source value.
3. **Provenance test case.** The patch claims provenance assertion; prove it with a synthetic test where the value exists ONLY in `*_개발본.hwpx` — the verifier must reject it. If that test doesn't exist, the original root cause may still be reachable.
4. **QDEV-2025-008 / QDEV-2025-020** must appear as human-anchor-blocked, not silently dropped.

---

## Part 2 — What actually changed 2023 → 2025 (the "connect the dots" result)

Full field-level detail in `iso_temporal_change_matrix_2023_2025.csv`. The changes fall into six classes:

### Class A — DATE_ROLL (~70% of all differences)
Dates advance, content identical. 작성일/등록일/심사일/자격등록일. Pattern is stable:
교육·계획 03월 중순 → 모니터링 04월 초 → 자격등록 05월 중순 → 내부심사 06월 초 → 등록부 05월 중순.
**2026 rule: generate dates from this calendar pattern; never treat a bare date as content.**

### Class B — STATIC (the majority of substance)
Monitoring targets (소음/진동 1년, 폐기물 월), legal references (소음진동규제법 제2조, 폐기물관리법 제26조),
education curriculum (5 courses, unchanged 2023=2024), process lists (원재료입고/자재/절단/용접/조립),
quality objectives (ISO 정착 + 원가절감 10%, unchanged 2023=2024).
**2026 rule: carry forward verbatim; only re-check law revision dates.**

### Class C — CONTENT_EVOLVED (business pivot)
식품제조/식품가공/음식 폐기물 → 제조/생산/폐기물 (2025 ENV package). The company de-food-ified its
descriptions. **2026 rule: use 제조/생산 terminology everywhere.**

### Class D — ORG_CHANGE (2024 QMS)
생산팀 → 제품생산&연구개발팀; NEW 제품허가팀; named auditors (허민/제품허가, 김현주/경영지원);
audit schedule expanded to 3 teams (added 15:00–16:30 slot).
**2026 rule: 3-team structure is the baseline; verify no further reorg before generating.**

### Class E — RECURRING/PARTIAL FINDINGS (audit trajectory)
- 문서관리대장 미작성: 2023 경영지원팀 → fixed → **2024 제품허가팀 (new team repeats the same finding)**
- 자재분류 관리대장: 2023 미작성 → 2024 "작성되었으나 세부 분류가 미흡함" (partial fix)
- 환경측면 실무자 교육 요구: raised 2023, **still open 2024**

### Class F — DEFECTS found in the historical documents themselves
1. **Incomplete term migration (ENV 2025):** "식품가공의 중요성" and "식품제조 활동에 의한 화재발생" survived
   the 식품→제조 rename (EP-601-03 p9, EP-805 훈련내용).
2. **Stale carry-forward (QMS 2024):** 위험성평가 보고서 still dated 2023.06.08 inside the 2024 package.
3. **3-year open action (ENV):** "분리수거함 제작/설치 요망" unresolved 2023 → 2025.
4. **Org-name mismatch:** 성과지표 산출표/방침실천서 still say 구매팀/생산팀/개발팀 after the reorg.

---

## Part 3 — Highest-probability 2026 issues (ranked)

These are the predictions the 2026 documents should be written around:

| # | Predicted 2026 issue | Basis (dots connected) | P |
|---|---|---|---|
| 1 | 원가절감 목표 3년 연속 "자료 부족으로 검토 미흡" — external auditor flags ineffective objective management (ISO9001 6.2/9.3) | Same objective + same failed-measurement remark 2023 AND 2024 | Very high |
| 2 | 환경측면 실무자 교육 부적합 재발 | Raised 2023, still open 2024, no closure evidence in 2025 ENV package | Very high |
| 3 | New/renamed team repeats 문서관리대장 미작성 | Deterministic pattern: every team's first audit produced this finding (경영지원 2023, 제품허가 2024) | High |
| 4 | Stale-date nonconformity: a 2023/2024-dated record (위험성평가, 법규점검) found inside the 2026 package | Already happened in 2024 package (위험성평가 2023.06.08) | High |
| 5 | 분리수거함 action item flagged as never-closed corrective action | Open since 2023 check sheet, verbatim unchanged in 2025 | High |
| 6 | Terminology inconsistency (식품 residue vs 제조) flagged during document review | 2 residual occurrences in 2025 ENV package | Medium-high |
| 7 | 성과지표: 12 of ~35 indicators marked implemented, rest never measured — scope-vs-practice gap | Static ● markers 2023=2024, no expansion | Medium |
| 8 | Legal register outdated: 폐기물관리법/소음진동관리법 amended since 2023 but register carries old 개정일 | Register only rolled years, never re-checked amendments | Medium |

**2026 목표 recommendation:** replace the static pair with measurable targets, e.g.
(1) 경영시스템 부적합 재발률 0% (전년 지적사항 재발 방지), (2) 원가절감 — 분기별 경비 데이터 산출 체계 구축 후
목표치 10% 유지, (3) 환경: 분리수거함 설치 완료 및 폐기물 발생량 전년 대비 5% 절감.

---

## Part 4 — How this unblocks the automation pipeline

The blocker was "cannot collect and sort out which information is to be used." The change matrix converts that
into a deterministic generation policy:

```
for each field in target 2026 form:
    STATIC              -> copy 2025 (ENV) / 2024 (QMS) value verbatim        [auto, WRITE candidate]
    DATE_ROLL           -> compute 2026 date from calendar pattern            [auto, WRITE candidate]
    CONTENT_EVOLVED     -> use latest terminology (제조/생산)                  [auto, WRITE candidate]
    DEFECT_*            -> corrected value, flag [CORRECTED_2026]             [auto + human confirm]
    ORG_*               -> latest org names, flag [ORG_CONFIRM]               [human confirm]
    RECURRING/CHRONIC   -> requires REAL 2026 activity data (실적/심사결과)     [human input only — never fabricate]
    OPEN_ACTION         -> closure evidence or documented reason              [human input only]
```

Critical boundary: **실적 (actual results), 심사 결과, 교육 참석자, 측정치 are human-input-only.** The pipeline
may pre-fill structure, plans, static values, and dates, but must never invent actuals — that is both an ISO
audit failure mode and the same false-evidence problem the V3 patch just fixed on the verification side.

## Part 5 — Execution order

1. Close Part 1 gaps (transition table for the 13 rows, provenance test, 6-row spot check).
2. Rebuild ISO14001 map from the change matrix: STATIC/DATE_ROLL/CONTENT_EVOLVED rows become WRITE rows
   with exact source values from the 2025 ENV package (not the 2023 one); map_lint must pass.
3. Zone-1 draft apply of WRITE rows into disposable copies; same-run XML verification with patched V3.
4. Human Hancom review incl. QDEV-2025-008/020; then 2026 drafts (`품질실적문서_2026_draft.md`,
   `환경실적문서_2026_draft.md`) get human-filled actuals before any final acceptance.
