# YEARLY ROLL-FORWARD AUTOMATION SPEC (v1)
## ISO supplement year-N → year-N+1 document generation — zero-inference edition

Derived from the actual 2025→2026 correction cycle (2026-07-06/07). Every rule below
exists because its absence caused a real defect in that cycle. Codex implements this
spec verbatim. **Codex makes no content decisions. Ever.** Where the cycle required
judgment, this spec replaces it with (a) a fixed template library, (b) a cell registry,
or (c) an operator answer file.

---

# PART 1 — WHY EACH FAILURE HAPPENED (the evidence base)

| # | Defect observed in the 2026 cycle | Root cause | Systematized as |
|---|---|---|---|
| F1 | Two draft files = sequential stages ("ISO14001/ISO9001" names) | lineage by filename, stages kept as siblings | S1 single-draft chain |
| F2 | 검토일 2025.03.11 next to 검토기간 2026.01-2026.03 | date updates done by search, no completeness list | Cell Registry (every mutable cell enumerated) |
| F3 | 유효기간 2026.05.16→2026.05.15 (expires before start) | blind year edit without semantic check | V-gate G4 date-logic assertions |
| F4 | 허민 ×4 remained after "cascade" | cascade done by memory, not sweep | S6 name sweep = zero-count gate |
| F5 | 2 teams' findings unevolved; checklist rows unmapped | evolution left to codex inference | Template Library + answer file (PART 3) |
| F6 | 경영검토 2.1 carried 2023-era findings | no rule linking 검토서 body to prior-year audit | R-FLOW-1 (fixed data-flow map) |
| F7 | Mashed/overlapped glyphs after edits | stale hp:linesegarray layout caches | R-LINESEG-1/2/3 |
| F8 | Table overflow pushing next page | text longer than cell capacity, honest layout revealed it | R-CAPACITY-1 + dual-text pattern |
| F9 | B9 content had no target form | form existence never checked before content prep | S2 form-inventory precondition |

---

# PART 2 — SYSTEM ARCHITECTURE

## Inputs (all versioned, all required before S3)
1. `BASE.hwpx` — the human-ACCEPTED year-N document (decision file must exist).
2. `cell_registry.csv` — the master enumeration (PART 4). Built once, maintained per template change.
3. `template_library.json` — finding-evolution + narrative templates (PART 3).
4. `answers_YYYY.json` — operator answer file for the target year (PART 5). ~30 min of human time.
5. `claims_YYYY.json` — pre-declared legitimate non-target-year tokens.

## Output
- `DRAFT_YYYY.hwpx` + full verification manifest + ONE consolidated review packet.

## State rule (fixes F1)
ONE working draft per target year. Stages live in run folders with parent-hash chaining;
never as sibling files with stage names. Any file not in the chain registry is dead.

---

# PART 3 — TEMPLATE LIBRARY (kills inference in the finding-evolution region)

## 3.1 Issue evolution state machine (operator rule: 1 issue per team per year,
## next year's issue = related successor; prior issue reduces/resolves)

Fixed progression templates (T*). {slots} are filled ONLY from answers_YYYY.json:

- T1_NOT_DONE:        "{대상}이(가) 작성되어 운영되고 있지 않음."
- T2_DONE_PARTIAL:    "{대상}은 작성되었으나 {세부요소}가 미흡함."
- T3_MAINTAINED_GAP:  "{대상}은 정비되었으나 {후속요소}(갱신/전파/적용/회수)가 지연되거나 일부 누락됨."
- T4_DONE_UNVERIFIED: "{활동}은 실시되었으나 {검증요소}(전 직원 전파/현장 적용/기록 확인)가 미흡함."

Yearly transition rule: state(team, year+1) = next template in chain (T1→T2→T3/T4→ new T1
on a NEW 대상 chosen by operator). The OPERATOR picks the slot values in the answer file.
Codex substitutes strings. No generation.

## 3.2 Dual-text rule (fixes F8)
Every finding carries TWO renderings in the answer file:
- `long`  — full sentence, used in wide cells (심사결과보고서 요약, 경영검토 body)
- `short` — ≤ 16 chars, used in narrow cells (감사점검표 비고)
Codex never derives short from long. Operator writes both (or approves proposed pair
in the packet BEFORE any write).

## 3.3 Checklist mapping table (fixes F5)
Static lookup: finding-topic → 감사점검표 row number.
  교육/전파      → row 11    문서 최신본/갱신 → row 14
  문서 식별/보관/구본 → row 15    심사절차/기록    → row 41
  (extend as topics appear; unknown topic = STOP_ASK_OPERATOR, never guessed row)
Rule: rows carrying PRIOR year's 부적합 whose issue is superseded → restore 적합, clear 비고.

## 3.4 Data-flow map R-FLOW-1 (fixes F6) — fixed, never re-derived
  심사결과보고서(year N) findings  ──feeds──▶ 경영검토서(year N+1) §2.1 (list + count)
  심사결과보고서(year N+1) findings ──feeds──▶ 감사점검표(year N+1) rows (3.3 map)
  findings(year N+1)               ──feeds──▶ 개선요구/통보서(year N+1), 1:1 trace
  자격등록(year N+1) 등록일          ──feeds──▶ 유효기간 = 등록일 + 1년 − 1일

---

# PART 4 — CELL REGISTRY (kills inference in the "what to update" region; fixes F2)

`cell_registry.csv`, one row per mutable cell. Columns:
  cell_id | form_code | anchor_before (unique context string) | anchor_after |
  fill_class | source_key (answers path / template id / DATE rule) |
  max_chars (from cellSz width ÷ char width at cell font) | verify_mode |
  claim_type (for non-target-year values)

fill_class enumeration (complete):
  DATE_ROLL_SAME_MD   — year→target, month/day preserved (operator-approved policy)
  DATE_FIXED          — explicit value from answers (e.g., 심사일)
  DATE_DERIVED        — computed (유효기간 = 등록일+1y−1d)
  NO_WRITE_HISTORY    — B1 register dates etc.; pre-claimed LEGIT_HISTORY
  NAME_ROLE           — from answers.people; participates in S6 sweep
  FINDING_LONG / FINDING_SHORT — from template substitution (3.1/3.2)
  NARRATIVE_SLOT      — risk/외주/고객 texts from answers, dual-text where narrow
  STATIC              — never changes; presence asserted, content untouched

Registry completeness gate: after S7, every changed text node must map to exactly one
registry row, and every registry row with a source value must have been applied.
Unmapped change OR unapplied row = RUN FAILS. (This is what "6 remaining dates" and
허민 ×4 lacked.)

---

# PART 5 — OPERATOR ANSWER FILE `answers_YYYY.json` (the ONLY inference input)

```json
{
  "target_year": 2026,
  "dates": { "검토일": "2026.03.11", "심사계획_작성일": "2026.05.23",
             "심사일": "2026.06.05", "심사결과_작성일": "2026.06.10",
             "위험성평가_보고일": "2026.06.11", "자격등록일": "2026.05.16",
             "policy_rest": "SAME_MONTH_DAY" },
  "people": { "내부심사원": ["성윤식", "김현주"], "대표이사": "이상진",
              "보고자": "성윤식", "교육참석자": ["김현주","홍지영","이상진"],
              "removed": ["허민", "<이전 대표이사>"] },
  "goal_change": { "mode": "MODIFY", "slot": 2,
                   "text": "교육 이행 및 전 직원 전파 체계 강화" },
  "findings": [
    { "team": "경영지원팀", "template": "T4_DONE_UNVERIFIED",
      "slots": {"활동": "환경측면 파악 및 영향평가 교육", "검증요소": "전 직원 전파 및 현장 적용 확인"},
      "short": "환경측면 교육의 전사 전파 미흡.", "checklist_topic": "교육/전파" },
    { "team": "제품생산&연구개발팀", "template": "T3_MAINTAINED_GAP",
      "slots": {"대상": "자재 분류 관리대장", "후속요소": "신규 원자재(헤파린 등) 분류 기준 갱신"},
      "short": "자재분류 기준 문서 갱신 지연.", "checklist_topic": "문서 최신본/갱신" },
    { "team": "제품허가팀", "template": "T3_MAINTAINED_GAP",
      "slots": {"대상": "문서관리대장", "후속요소": "개정 문서의 구본 회수 및 폐기 처리"},
      "short": "구본 회수/폐기 일부 누락.", "checklist_topic": "문서 식별/보관/구본" } ],
  "risk": { "대상_short": "(주)우리비앤비 파산(헤파린 공급업체)",
            "의견_추가_short": "※ (주)우리비앤비 파산 발생. 대표가 아티젠테라퓨틱스 신설, 공급 지속. 대체 공급처 발굴 필요." },
  "b9_외주": { "업체": "경희대학교 권일근 교수 연구실", "분야": "바이오잉크 제조 및 판매", "..." : "..." },
  "b9_고객": { "고객": "연구소", "프로젝트": "바이오잉크 연구·실험", "근거": "구두 만족 확인", "tone": "scientific" }
}
```
Missing key referenced by any registry row = RUN BLOCKS with a question packet.
Codex never fills a gap with a guess.

---

# PART 6 — THE EDIT ENGINE (exact algorithm, fixes F3/F4/F7/F8)

## E1. Safe replace primitive (only mutation allowed)
```
replace(raw, old, new, expected_count, context_anchor=None):
    if context_anchor: operate only in [anchor_start, next_form_boundary]
    assert raw.count(old_in_scope) == expected_count  → else ABORT run
    perform replace; log (cell_id, old, new, position)
```
Node-level variant for split-run text: clear all <hp:t> in the target tc, set first
to new value (never author new elements except expanding a self-closed
<hp:run charPrIDRef="N" /> to carry one <hp:t> — reusing the existing charPrIDRef).

## E2. R-LINESEG rules (fixes F7 — the mash)
- R-LINESEG-1: any paragraph whose text length changed → DELETE its <hp:linesegarray>.
  (Cache is optional; Hancom recomputes on open. Stale cache + longer text = guaranteed mash.)
- R-LINESEG-2 (guard): layout QA flags any paragraph where text ≠ base but
  linesegarray == base. That combination is a mash by construction.
- R-LINESEG-3: session end → Hancom COM open + SaveAs roundtrip regenerates all caches
  before render QA and human review.

## E3. R-CAPACITY-1 (fixes F8 — the overflow)
Before every write: lines_needed = ceil(len(new) / floor(cell_width_hwpu / char_width_hwpu)).
char_width_hwpu ≈ font vertsize (Korean full-width). If lines_needed > cell's current
line capacity → REJECT the write and demand the `short` variant from the answer file.
Never resize the table, never shrink the font, never let the row grow past its page.

## E4. Forbidden (unchanged from geometry policy)
No structural change (rows/cols/merges/sz), no orientation change, no font-size change,
no table resize, no new charPr/paraPr authoring, no edits outside registry rows.

---

# PART 7 — PIPELINE STEPS (S0–S12, executed in order, no skips)

S0  PRECONDITION: BASE.hwpx has an acceptance decision file. Hash-register it as chain root.
S1  COPY BASE → working draft in run folder; record parent SHA-256. (F1)
S2  FORM INVENTORY: assert every registry form_code + every answers key has a target
    form in the document. Missing form (e.g., B9 협력업체평가) → BLOCK with
    FORM_ADDITION_REQUIRED packet (donor-assembly task, separate declared pass). (F9)
S3  FREEZE MANIFEST: sections/pagePr/tables/sz/rows/cols/merges snapshot.
S4  RESOLVE registry: every anchor_before must locate exactly once. 0 or 2+ hits = BLOCK.
S5  APPLY: iterate registry rows in document order; E1 primitive per row; E2/E3 enforced
    inline. DATE_DERIVED computed (G4 asserts 유효기간 > 등록일 etc.).
S6  SWEEPS (all zero-tolerance):
    - year sweep target=YYYY: every non-target token must match claims_YYYY.json
    - name sweep: every answers.people.removed name count == 0
    - malformed-date regex: r'20\d\d\.\d{3,}' and r'20\d{6}' count == 0
    - marker sweep == 0
S7  COMPLETENESS: changed-node set == applied registry rows, both directions. (PART 4 gate)
S8  FREEZE CHECK vs S3: zero structural delta (FORM_DUPLICATE only if declared in answers).
S9  LINESEG QA (R-LINESEG-2) then COM SaveAs roundtrip (R-LINESEG-3).
S10 RENDER: Hancom render hook → page count must equal BASE page count (± declared
    duplications); pixel-diff pages vs BASE — diffs allowed only on pages containing
    registry-row cells.
S11 REVIEW PACKET: one dashboard — every changed cell before/after, capacity math,
    sweep claims tables, findings trace (finding → 검토서2.1 → 점검표 row → 통보서).
S12 HUMAN GATE: operator pasteback. No FINAL_ACCEPTED without explicit decision file.

---

# PART 8 — REGRESSION FIXTURE (locks the whole system)

The executed 2025→2026 cycle is the reference test:
input = accepted 2025 SCAN_RECONCILED base + the answers embodied in this cycle
expected output = V3 text state: {2025:31(all B1), 2026:36, 2027:2}, 허민=0, 성윤식=10,
mash-cells absent (lineseg count 0 in section0), 점검표 부적합 rows = {11,14,15},
row41 적합, 검토서2.1 = 3-team 2025 findings, capacity violations = 0.
Codex must reproduce this from inputs before the system is trusted on 2027.
(2027 then costs: one answers_2027.json + one operator review. Nothing else.)

---

# PART 9 — INFERENCE CONTAINMENT SUMMARY (the user's core requirement)

| Region where inference was needed in the manual cycle | Who does it now |
|---|---|
| Which cells to update | cell_registry.csv (enumerated once) |
| What the new dates are | answers.dates + DATE rules + G4 assertions |
| Who replaces whom | answers.people + zero-count sweep |
| How findings evolve | template chain T1→T4 + operator slot values |
| How long text fits narrow cells | operator-authored `short` variants + R-CAPACITY-1 |
| Which checklist row a finding maps to | static topic→row table; unknown topic = ASK |
| Risk/외주/고객 narratives | answers narrative slots, verbatim substitution |
| Anything not covered above | STOP_ASK_OPERATOR. Always. |

Codex's remaining role: file operations, string substitution with assertions,
sweeps, rendering, packaging. All falsifiable, none creative.
