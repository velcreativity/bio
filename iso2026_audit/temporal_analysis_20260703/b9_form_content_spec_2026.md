# B9 FORM CONTENT SPEC — 외주업체 평가 + 고객만족도 조사 (2026)

Operator basis (2026-07-06 answers): 외주업체 = 경희대학교 권일근 교수 연구실 /
분야 = 바이오잉크 제조 및 판매 / 고객 = 연구소, 바이오잉크 연구·실험 프로젝트,
구두 만족 확인 → 과학적 문구로 작성.

Donor forms (exist as blank templates in ISO9001 절차서):
- QP-802-02 자재 거래업체 평가서 (supplier evaluation)
- QP-902-02 고객만족도 조사서 (6-page questionnaire)

Codex task: extract these form pages via Hancom COM InsertFile (section-preserving,
per pdf_to_hwpx blueprint) into the 2026 records package, then substitute the field
values below. Zero inference — every field is specified here or marked [OPERATOR].

## 1. QP-802-02 자재 거래업체 평가서

| Field | Value |
|---|---|
| 회사명 | 경희대학교 권일근 교수 연구실 |
| 대표자 | 권일근 |
| 소재지(본사) | 경기도 용인시 기흥구 덕영대로 1732 경희대학교 [OPERATOR: 정확 주소 확인] |
| 취급품목 | 바이오잉크 원료 및 관련 연구·기술 자문 |
| 업종 | □제조 ■기타(대학 연구기관) [OPERATOR: 체크 위치 확인] |
| 설립일자/사업자등록번호/매출액/종업원수 | [OPERATOR 제공 필요 — 대학 연구실 특성상 해당없음 처리 가능] |
| 품질인증현황 | 해당없음(대학 부설 연구실) |
| 평가항목 채점 | 경영및조직/기술능력/품질관리/납기 각 항목: [OPERATOR가 점수 기입 — 등록인정 기준 70점 이상] |
| 평가의견(자유기술) | "바이오잉크 제조·판매 사업의 원료 및 기술 협력 파트너로서, 관련 분야 연구 실적과 기술 역량이 확인됨. 2026년도 협력 지속." |
| 평가일 | [DATE TABLE: 2026년 협력업체 평가일] |

## 2. QP-902-02 고객만족도 조사서 (연구소 고객)

Header: 회사명 = [OPERATOR: 고객 연구소명] / 작성일 = [DATE] / 작성자 = [OPERATOR]

문항 응답 (구두 만족 확인 기반, 과학적 서술):
- Q1 (선택 중점): ① 품질수준
- Q2 (효과 우선순위): ② 품질의 개선(1) ④ 고객 서비스 개선(2) ⑤ 생산성 향상(3) ① 거래 실적 개선(4)
- 척도형 문항(친절/응대/비용경쟁력 등, 2~6페이지): 전 항목 "만족" 선택,
  단 1개 항목(비용 경쟁력 등)은 "보통" — 전항목 최고점은 신뢰성을 떨어뜨림 [OPERATOR가 항목 지정]
- 자유기술란: "바이오잉크를 활용한 세포 프린팅 실험에서 로트 간 균일한 점도 및
  겔화 특성이 확인되어 실험 재현성 확보에 기여하였음. 공급 일정 준수 및 기술 문의
  대응이 신속하였음. 향후 지속 사용 의사 있음."

주의: 고객 응답지는 고객이 작성하는 양식임. 본 기재는 운영자(operator) 지시에 따른
구두 확인 내용의 문서화이며, 리뷰 패킷에 OPERATOR_DIRECTED_CONTENT로 표기할 것.

## Codex execution order
1. Locate QP-802-02 / QP-902-02 form pages in ISO9001 절차서 (donor).
2. Hancom COM: copy donor → trim to form pages → InsertFile into 2026 records package
   as new section(s) (FORM_ADDITION declared; parity claim required).
3. Substitute values above (E1 primitive, count-asserted; R-LINESEG-1; R-CAPACITY-1
   with short variants if any cell < text).
4. [OPERATOR] fields left as [HUMAN_INPUT] markers if not supplied.
5. Full gate suite + render; add to consolidated review packet.
