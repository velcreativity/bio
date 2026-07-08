# ISO 2026 프로젝트 — 세션 마스터 인덱스

바이오프렌즈 ISO9001/14001 문서 자동화 세션의 전체 산출물 색인 및 확정 사실.
원시 문서(HWPX/PDF/HWP)는 git 정책상 제외 — 사용자에게 직접 전달됨.

## 확정된 2026 비즈니스 사실 (전 문서 공통 권위)
- 대표이사: 이상진 (구: 허동녕)
- 내부심사원: 성윤식, 김현주 (구: 허민, 김현주 — 허민 완전 교체)
- 생산 담당/반장: 홍지영 (2026), 허민 (2025 거래)
- 경영검토: 검토기간 2026.01–2026.03, 검토일 2026.03.11
- 자격 유효기간: 등록일+1년−1일 (2026.05.16 → 2027.05.15)
- 2026 심사 findings (팀별 1건, 전년 대비 진화):
  - 경영지원팀: 환경측면 교육 실시했으나 전 직원 전파 미흡
  - 제품생산&연구개발팀: 자재분류 관리대장 세부는 정비, 신규 원자재(헤파린) 기준 갱신 지연
  - 제품허가팀: 문서관리대장 운영 중, 개정문서 구본 회수/폐기 일부 누락
- 감사점검표: 부적합 행 11·14·15, row41 적합 복귀
- 위험: (주)우리비앤비(헤파린 공급) 파산 → 대표가 아티젠테라퓨틱스 신설, 공급 지속, 대체 공급처 필요
- B9 외주평가: 경희대 권일근 교수 연구실 (바이오잉크 원료/기술)
- B9 고객조사: 연구소, 바이오잉크 연구·실험, 구두 만족 (과학적 문구화)
- 경영검토서 "2017년 신규 규격…항목이 없음" 문단 삭제

## 2026 거래 실적 (거래명세서 4건 — 거래명세서_추출데이터_4건.csv)
- 2025.09.26 동국대 김진식: Hyaluronate + ColMA (2,840,000) [구 조직]
- 2025.10.23 동국대 김진식: GelMA+Platelet+PLMA (2,160,000) [구 조직]
- 2026.03.26 숙명여대 신영민: Platelet+ColMA+GelMA (2,739,000) [현 조직]
- 2026.04.23 조선대 김병훈: ColMA (2,640,000) [현 조직]
→ 각 거래별 작업지시서 세트(QP-804-01/02/03) 4건 생성 완료 (사용자 전달).

## 산출물 색인
### 시계열/기획
- iso_temporal_change_matrix_2023_2025.csv — 36필드 변경 분류
- iso2026_projection_report.md — 2026 예측 이슈
- 품질실적문서_2026_draft.md / 환경실적문서_2026_draft.md
### 자동화 규칙/스펙
- yearly_rollforward_automation_spec.md — 무추론 연도 롤포워드 파이프라인 (핵심)
- iso2026_build_procedure_no_freedom.md — 제로-자유도 빌드 절차
- table_geometry_change_policy.md — 표 크기/방향 변경 정책
- content_fill_directive_layout_frozen.md — 레이아웃 동결 채움
- pdf_to_hwpx_failure_analysis_and_blueprint.md — PDF→HWPX 실패 근본원인+청사진
- ocr_format_reconstructor.py — 도너 없는 스캔 재구성 (측정 기반)
- history_review_rules_and_subagents_20260703.md — 규칙+서브에이전트 아키텍처
- rep_loop_harness.py / rep_loop_orchestrator_prompt.md — 자율 학습 루프
### 진행 관리
- iso2026_completion_ledger.csv (25항목) / iso2026_completion_directive.md
- 2026_실적모음_완성도_점검.md — 실적모음 완성도 (최신)
- b9_form_content_spec_2026.md / b7_통보서_content_and_form_addition_spec.md
### 검토
- iso14001_clean_rebase / date_roll_hancom_review_checklist.html
- visual_cleanup_plan_20260703.md

## 현재 상태 (2026-07-07)
- ISO9001/14001 절차서: 무변경 확정 (인명 없음·이력 보존·용어 정상).
- 품질실적모음_2026: 사실상 완성. 누락 = QP-802-02/QP-902-02 폼 2개(B9) 삽입+기입.
- 환경실적모음_2026: 대폭 미완성. 환경실적 2025.hwp(바이너리) 필요.
- 두 누락 모두 구조적 폼 추가 = Hancom COM(Windows/코덱스) 필요.
  원시 XML 재조립은 crash 발생(검증됨) → 금지.

## 핵심 기술 교훈 (전 세션 누적)
1. HWPX 유효 작성은 Hancom만 신뢰 가능 (원시 XML = dangling style-ref → crash).
2. 도너 텍스트 = 서식이지 내용 아님 (연도 잔재 방지 규칙 A1).
3. 날짜 맹목 롤 금지 (일자도 변함), 이름 변경은 전수 sweep.
4. hp:linesegarray 캐시 = 편집 시 삭제해야 (mash 방지).
5. 셀 용량 초과 시 표 확대 금지 → 텍스트 단축.
6. 폼 추가/구역 분리 = Hancom COM (container.rdf/content.hpf 정합성 필수).
