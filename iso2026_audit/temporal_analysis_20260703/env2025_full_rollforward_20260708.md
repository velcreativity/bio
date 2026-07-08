# 2025 환경 문서 → 2026 환경심사 전량 롤포워드 — 2026-07-08

Correction: the V4 supplement's EMS portion held only 4 forms. The REAL 2025 환경 document
(user-provided `..._2025_.hwpx`) has **11 form types across ~18–20 pages**. Page-count claim
verified: NOT 4.

## Real 2025 환경 document inventory (3 sections)
EP-601-01 환경측면 파악표 ×2 · EP-601-03 환경영향 등록부 ×2 · EP-602-01 환경법규 등록대장 ·
EP-602-02 환경법규 점검표 ×2 · EP-603-01 년간 환경목표 · EP-603-02 환경방침실천 계획/실적서 ×2 ·
EP-603-03 환경 직무기술서 ×2 · EP-805-01 비상사태 종료보고서 · EP-805-02 비상사태 훈련 계획서 ·
EP-901-01 모니터링/측정 계획서 · EP-901-02 모니터링/측정 CHECK SHEET · 환경교육훈련 계획서 + 교육결과보고서.

## Key finding: no Hancom needed for EMS
Because every form already exists in the 2025 doc, 2026 generation = text-only roll-forward
(the safe operation), NOT page insertion. Output: 환경심사_2026_FULL_V1.hwpx (all 11 forms, validated).

## Applied (환경심사_2026_FULL_V1)
- Dates → 2026 (operational only): 2025년 ×7, 2025. ×11, 3/18.2025 ×2.
- LAW REGISTER PRESERVED: EP-602-01 폐기물관리법/소음진동관리법 제정일·개정일 (bare 2023 ×12, bare 2025 ×2)
  intentionally NOT rolled (permanent legal history).
- 식품 잔재 정정 ×2: 식품제조 활동→제조 활동 (EP-805 훈련내용); 식품가공의 중요성→제품 생산의 중요성 (EP-601-03).
- 분리수거 종결: 분리수거함제작/설치요망 → 분리수거 시스템 정상 운영 (EP-901-02, operator: 신규 사업장 자체 분리수거).
- 2319 linesegarray caches stripped. Title→2026. Gates: zip/XML/style-ref(0 dangling)/manifest PASS.

## Remaining fill items (need real values / cell targeting)
1. 년간 환경목표 (EP-603-01): enter approved 3안 (분리수거 완료 / 폐기물 5% 절감 / 교육 100%) — goal cells sparse in 2025, needs targeting.
2. 폐기물관리법 개정일 (EP-602-01): real latest amendment date (operator: 개정일만 갱신 OK) — value needed.
3. 비상사태 훈련/종료일 (EP-805): rolled to same M/D (2026.03.24–03.31); confirm actual 2026 drill dates.
4. 교육결과보고서: 참석자/결과 HUMAN_ONLY.
5. Names: env forms carry no 대표이사/심사원 personal names (unlike QMS) — no sweep required.
