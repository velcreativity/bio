# V4 Supplement Error Audit & Quality/Environment Split — 2026-07-08

Input: `ISO2026_SUPPLEMENT_DRAFT_FABLE5_CORRECTED_V4.hwpx` (user-provided, 37 pages, 4 sections).
Output: `품질심사_2026_V5.hwpx` (sections 0–1) + `환경심사_2026_V5.hwpx` (sections 2–3), delivered
directly to user (R6: binaries never enter git).

Method: text-only in-place cell edits + package-level section split. NO form insertion, NO table
geometry change, NO cross-file XML transplantation (per verified crash lesson — those remain
Hancom COM tasks).

## A. Errors found in V4 and fixed (V5)

| # | Class | Location | Before → After | Count |
|---|---|---|---|---|
| 1 | GOAL_MISMATCH | QP-501-01 년간목표 항목3 (empty) | filled: 원가절감 ( 전년도대비 10% ) | 1 |
| 2 | GOAL_MISMATCH | QP-903 세부내용 1.1 | added ▷ 교육 이행 및 전 직원 전파 체계 강화 (order matches 목표표) | 1 |
| 3 | GOAL_MISMATCH | QP-501-02 실천계획서 #2 title | 교육 이행… → 원가절감 ( 전년도대비 10% ) — body was already the 원가절감/경비 plan | 1 |
| 4 | STALE_DATE | QP-903 심사결과 | 2017년 전사원이 → 2026년 전사원이 | 1 |
| 5 | ORG_CHANGE | 실천계획서/성과지표 등 | 구매팀 → 경영지원팀 | 7 |
| 6 | ORG_CHANGE | 전 구역 | 생산팀 → 제품생산&연구개발팀 (ledger 배포처 legend 포함) | 11 |
| 7 | ORG_CHANGE | 경영검토서/성과지표 (whole-cell) | 개발팀 → 제품생산&연구개발팀 | 2 |
| 8 | DONOR_RESIDUE | QP-401-01 이슈현황표 | 시공팀 (건설사 donor 잔재) → 제품생산&연구개발팀 | 1 |
| 9 | DEFECT_DANGLING_REF | section1 (QP-401 현황표) | charPrIDRef 191/193 undefined in header (ids 0–134) → remapped to 19. **Pre-existing in V4; latent Hancom crash risk (empty spacer runs)** | 5 |
| 10 | TYPO | QP-903/QP-705 등 | 원감절감→원가절감(2), 관합법률→관한 법률, 전박적인→전반적인, 관계계자→관계자, 끼타→기타, 계획서의 개성→개정, 정지적으로→정기적으로, 해당없슴→해당없음(3), 추정성관리→추적성관리 | 12 |
| 11 | FORMAT | footers | REV.O (letter O) → REV.0 | 11 |
| 12 | CACHE | sections 1–3 | hp:linesegarray stripped (657 caches; lesson 4 — viewer recalculates) | 657 |
| 13 | METADATA | content.hpf | corrupt binary garbage in opf:meta name="date" sanitized; per-file opf:title set | 2 |

Goal-consistency decision (user-directed): 원가절감 added as goal 3 instead of overwriting goal 2,
because 실천계획서 #2's body was already the 원가절감 plan while 교육 had title only.

## B. Split integrity

- Section boundary is clean: sec0–1 = QMS only, sec2–3 = EMS only (verified no cross-contamination).
- Per-file updates: content.hpf manifest+spine, container.rdf SectionFile entries, header secCnt 4→2,
  env sections renumbered 2→0/3→1, PrvText.txt regenerated from actual first-page text
  (fixes stale 2024.03.11 preview cache), env caret reset.
- Validation gate (both files): zip structure (mimetype first, STORED) PASS · XML well-formedness
  (all xml/hpf/rdf) PASS · style-ref resolution (charPr/paraPr/style/borderFill) 0 dangling PASS ·
  manifest/spine/secCnt agreement PASS · content probes PASS.

## C. Still missing — Hancom COM tasks (cannot be done safely by raw XML)

1. **QP-802-02 자재 거래업체 평가서** — data confirmed in b9_form_content_spec_2026.md (경희대 권일근 연구실).
2. **QP-902-02 고객만족도 조사서** — data confirmed in b9 spec (연구소/바이오잉크, 과학적 문구).
3. **실천계획서 sheet for goal 2 (교육 이행)** — new gap created by goal-3 restore: 교육 goal now has
   no 방침실천 계획/실적서 page. Duplicate QP-501-02 form via Hancom and draft 교육 추진방안.
4. QP-903 세부내용에 교육 목표용 "계획 및 실적" 소절 없음 (1.2 원가절감/1.3 정착만 존재) — human decision.
5. 환경심사 file still holds only 4 EP forms; full EMS set requires 환경실적 2025.hwp conversion
   (per 2026_실적모음_완성도_점검.md plan D).

## D. Flags needing human confirmation (not changed)

- 위험성평가 보고서/위험관리 현황표 footers read **QP-603-01/02** but the procedure ledger has no
  QP-603 (위험관리 = QP-601). Form-code numbering anomaly — confirm correct codes.
- 위험성평가 보고서 보고자 blank (HUMAN_ONLY field).
- 문서관리대장 제정일 2025.03.11 with all Rev columns empty — per roll-forward rule QMS-001, a 2026
  revision should be recorded in the Rev.B column, not by re-rolling 제정일. Confirm whether Rev.B
  dates should be entered.
- org-name mapping 구매팀→경영지원팀 is an inference (ledger F23 marks org names as CONFIRM);
  veto and remap if purchasing sits elsewhere.
- Long team name 제품생산&연구개발팀 will wrap to two lines in narrow 담당부서 columns
  (R-CAPACITY: no table enlargement performed).
