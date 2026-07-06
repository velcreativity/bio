# ISO 2026 BUILD PROCEDURE — prescriptive, zero-freedom edition

Codex: execute exactly as written. Every decision point is marked STOP_ASK_USER.
Nothing outside this document may be inferred, improved, or "helpfully" changed.

===========================================================================
PART A — CODEX CORRECTION: rules that prevent the year-residue error class
===========================================================================

The 2025 build failure (62 wrong year tokens) happened because donor text was
treated as content. These rules are now permanent:

A1. DONOR TEXT IS FORMAT, NOT CONTENT.
    Every value-bearing cell inherited from a donor must be either
    (a) explicitly rewritten from the target-year source, or
    (b) explicitly claimed CARRY_FORWARD in the map with a reason.
    An unclaimed inherited value fails the run.

A2. YEAR-RESIDUE SWEEP IS A MANDATORY GATE (target_year parameter).
    After any content pass: every year token != target_year must be claimed:
      LEGIT_HISTORY   (e.g., 제정내역 2025.03.11 in a 2026 doc)
      LEGIT_SPAN      (e.g., 자격 유효기간 2026.05->2027.05)
      LEGIT_REFERENCE (e.g., "전년도" comparisons)
    Unclaimed foreign-year token = RUN FAILS. No exceptions.

A3. DATES ARE NEVER BLIND-ROLLED.
    Proven by evidence: 2024.05.24 -> 2025.05.23 (day changed, not just year).
    Every date write requires a declared source: the user-approved DATE TABLE
    (Part C Step 3) or a readable source document cell. Pattern-guessing a
    date is fabrication.

A4. NAME/ROLE CASCADE RULE.
    When a person or role changes, sweep the WHOLE document for every
    occurrence and list them all in the map before writing any. A name is
    never changed in one form only.

A5. HANDWRITTEN ANNOTATIONS ARE HUMAN DECISIONS.
    If a source scan carries handwritten corrections/strikethroughs, list
    them as STOP_ASK_USER items. Never silently choose printed vs handwritten.

===========================================================================
PART B — BUSINESS FACTS TABLE (sole authority; from user 2026-07-06)
===========================================================================

| # | Item | 2026 instruction | Class |
|---|------|------------------|-------|
| B1 | 관리대장 제정내역 | DO NOT MODIFY. 제정 dates stay as-is; claim LEGIT_HISTORY in year sweep | NO_WRITE |
| B2 | 경영검토서 검토기간/검토일 | 1-year cycle: 검토기간 2026.01–2026.03; 검토일 = DATE TABLE | WRITE |
| B3 | 품질 방침 및 목표 | Modify ONE goal or add ONE new goal per year | STOP_ASK_USER |
| B4 | 직무기술서 + 교육결과보고서 | Fill 보고자/성명 + 교육참석자 names | STOP_ASK_USER (names list) |
| B5 | 사내 자격등록 (내부심사원) | 허민, 김현주 -> **성윤식, 김현주** | WRITE + A4 CASCADE |
| B6 | 내부심사보고서 검사결과요약 | Slightly modified findings each year | PROPOSE -> STOP_ASK_USER |
| B7 | 지속적 개선요구/통보서 | Derived from B6 approved findings, written as composite items | WRITE after B6 |
| B8 | 회사소개서 | Address current; 대표이사 -> **이상진** | WRITE + A4 CASCADE |
| B9 | 외주업체 평가 + 고객조사 | Content based on research projects; USER WILL SUPPLY | STOP_ASK_USER (data request) |

B5 cascade targets (minimum; sweep for more): 자격등록대장, 심사계획서 심사원란,
심사일정표 심사요원, 심사결과보고서, 감사점검표 심사자, 개선요구서 발행부서란.
B8 cascade targets: 회사소개서, 년간목표 대표이사 서명영역 인접 텍스트, any
occurrence of the former CEO name anywhere in the package.

===========================================================================
PART C — BUILD STEPS (execute in order; no reordering, no skipping)
===========================================================================

STEP 0. PREREQUISITE GATE
  - The 2025 supplement candidate must first be finished: apply the 6
    remaining date corrections (년간목표 2025년, 세부내용 2025년도,
    심사계획서/일정표 2025.05.23, 심사결과보고서 date from scan p33,
    보고일 pair from scan) verified against scan pages, then pass human
    visual review. The ACCEPTED 2025 document is the 2026 donor.
  - STOP if 2025 is not human-accepted. Do not start 2026 on an unaccepted base.

STEP 1. BASE COPY + FREEZE
  - Copy accepted 2025 -> ISO_2026_draft workspace (new lineage, parent hash).
  - Snapshot freeze manifest (sections/pagePr/tables/sz/rows/cols/merges).
  - Structure changes in this build: NONE expected. FORM_DUPLICATE only if a
    STOP_ASK_USER answer requires an extra record.

STEP 2. NO-WRITE LIST (from B1)
  - Mark 관리대장 제정내역 cells as NO_WRITE in the map.
  - Their 2025 tokens are pre-claimed LEGIT_HISTORY.

STEP 3. DATE TABLE — PROPOSE, THEN STOP_ASK_USER
  - Produce the complete proposed date table: every dated field in the
    package | 2025 value | proposed 2026 value | basis (calendar pattern).
  - Present to user. USER APPROVES OR EDITS EACH ROW. Codex writes nothing
    until the table returns approved.
  - After approval: apply as DATE_WRITE (EXACT_CELL_MATCH verify).

STEP 4. B5 + B8 CASCADES
  - Sweep for 허민 (auditor contexts) and former CEO name: full occurrence list.
  - Map every occurrence: 허민 -> 성윤식 (auditor role contexts only;
    if 허민 appears in a non-auditor context, STOP_ASK_USER), CEO -> 이상진.
  - Apply, verify each cell.
  - New auditor 자격등록: registration/valid dates from DATE TABLE;
    유효기간 ending 2027 is pre-claimed LEGIT_SPAN.

STEP 5. B2 검토서 PERIOD + B3 GOALS
  - Write 검토기간 2026.01–2026.03, 검토일 from DATE TABLE.
  - B3: present the user two options with concrete candidates:
      (a) modify one existing goal (candidates from projection report:
          원가절감 목표의 측정체계 구체화)
      (b) add one new goal (candidates: 부적합 재발률 0%, 제품허가팀 문서관리
          정착, 환경: 분리수거함 완료/폐기물 5% 절감)
    STOP_ASK_USER. Write exactly what the user picks, verbatim.

STEP 6. B6 AUDIT FINDINGS — PROPOSE, THEN STOP_ASK_USER
  - Draft 2026 검사결과요약 as a MODIFICATION of the accepted 2025 findings
    using the recurring-findings trajectory (partial fixes progress, new team
    document-control items close, one new minor finding per team maximum).
  - Present draft verbatim to user. Write only the approved text.

STEP 7. B7 개선요구/통보서
  - Generate from the APPROVED B6 findings only: composite 부적합사항 per
    통보서, with 원인분석/조치내용 텍스트 consistent with the findings.
  - Present alongside B6 output for the same user approval; write after approval.

STEP 8. B4 NAMES — STOP_ASK_USER
  - Request the names list: 직무기술서 성명(2+ forms), 교육결과보고서
    보고자 and 교육참석자 per session.
  - Write exactly the supplied names. Empty answer = leave [HUMAN_INPUT] marker.

STEP 9. B9 외주업체 평가 + 고객조사 — STOP_ASK_USER (data request)
  - Produce a structured question packet: exact fields needed
    (업체명, 평가항목별 점수, 조사기간, 응답 요약 ...), one question per cell
    group, referencing the form layouts.
  - WAIT for user answers. No placeholder invention. Write supplied values only.

STEP 10. VERIFICATION GATE (all mandatory, one run)
  - V3 per-cell (declared modes) on every written cell
  - Freeze check vs Step 1 manifest (deltas = claimed FORM_DUPLICATEs only)
  - YEAR SWEEP target_year=2026: claims = LEGIT_HISTORY (B1), LEGIT_SPAN
    (자격 2027), LEGIT_REFERENCE (전년도 mentions); anything else FAILS
  - NAME SWEEP: zero unclaimed 허민/former-CEO occurrences
  - marker sweep, BinData check, parity delta attribution
  - render via hancom_render_hook: page count explained; layout QA green

STEP 11. ONE consolidated human review packet
  - Single dashboard: all changed cells with before/after, all STOP answers
    quoted as decision records, year/name sweep claims table.
  - State: HUMAN_VISUAL_REVIEW_READY. Never FINAL_ACCEPTED without the
    explicit acceptance decision file.

===========================================================================
PART D — WHAT CODEX MAY NOT DO (explicit)
===========================================================================
- No date invention or blind year-rolling (A3)
- No goal drafting beyond the B3 candidates without user approval
- No audit finding invention beyond B6 proposal->approval flow
- No names from anywhere except the user's B4 answer
- No B9 content of any kind before user data arrives
- No structural change, no orientation change, no table resize (geometry policy)
- No touching B1 cells
- No skipping STOP_ASK_USER gates, no batching them away, no assuming answers
