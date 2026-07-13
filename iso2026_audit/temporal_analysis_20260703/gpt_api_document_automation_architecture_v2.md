# 문서자동화 시스템 아키텍처 v2 — GPT API 기반 (사고이력 반영판)

기반: GPT 제안 아키텍처(React/FastAPI/OpenAI Responses API/Structured Outputs) + 이 프로젝트의
실제 사고 기록(11 결함 → 12 규칙, `history_review_rules_and_subagents_20260703.md`,
`yearly_rollforward_automation_spec.md`). GPT 원안에서 유지하는 것: 계층 구조, Structured
Outputs, gateway 패턴, `store=False`, 서버측 키 관리. 아래는 **변경·추가분만** 기술.

---

## 0. 전체 구조 (수정판)

```text
[사용자 화면] React 웹 / Tauri
        │
        ▼
[FastAPI 백엔드]
로그인·권한·프로젝트·작업 관리
        │
        ├─ ① 문서 전처리 (ingest/)
        │     HWPX/DOCX/PDF 추출 + HWP바이너리 변환요건 검사
        │     → source_inventory (값+출처 인용, 연도 태그)
        │
        ├─ ② 셀 레지스트리 (registry/)          ★신설
        │     양식별 mutable-cell 전수 등록
        │     anchor / max_chars / fill_class / verify_mode
        │
        ├─ ③ LLM Gateway (llm_gateway/)
        │     provider-agnostic (OpenAI 기본, Claude 등 폴백/AB)
        │     프롬프트 버전·비용·재시도·마스킹
        │
        ├─ ④ 필드 통제 게이트 (policy/)          ★신설
        │     HUMAN_ONLY 하드 블록, fill_class 화이트리스트
        │
        ├─ ⑤ 문서 출력 엔진 (writer/)            ★재정의
        │     "생성" 금지 → 원본 보존 + <hp:t> 치환만
        │
        ├─ ⑥ 검증 엔진 (verifier/)               ★위치 이동: 쓰기 후
        │     round-trip 재추출 대조 + 잔재 스윕 + 날짜 의미검증
        │
        └─ ⑦ 승인/이력 (audit/)
              결정파일 + draft parent-hash 체인 + run 레지스트리
```

핵심 순서 변경: 원안은 `검증 → 삽입`, 수정판은 **`삽입 → 산출물 재검증`** (검증은 양쪽 다 하되
최종 판정은 파일 기준).

---

## 1. 출력 엔진 (writer/) — 최우선 원칙

**HWPX는 생성하지 않는다. 원본을 보존하고 텍스트 노드만 치환한다.**

근거(실증): raw XML로 표/페이지 삽입 → dangling style-ref → 한글 crash (검증된 사고).
원본 V4에서도 dangling charPr 191/193 발견 — 한글 밖에서 만들어진 구조 변경의 전형적 결과.

```text
writer/
├─ hwpx_cell_writer.py     # anchor 기반 <hp:t> 치환 전용. 구조 변경 API 없음.
├─ docx_cell_writer.py     # python-docx, 동일 원칙
├─ package_rebuilder.py    # zip 재조립: mimetype first+STORED, manifest 정합
├─ post_write_gates.py     # 쓰기 직후 필수 게이트 (아래 §6과 별개로 즉시 실행)
└─ hancom_com_worker/      # (Windows 전용, 큐 기반) 폼 삽입·구역 분리·HWP 변환
```

규칙:
- W1. 셀 치환 시 anchor 유일성 assert (count==1 아니면 실패, 유사매칭 금지)
- W2. content 길이 > max_chars → 표 확대 금지, 실패 처리 후 short-variant 요청 (F8 방지)
- W3. 편집된 문단의 `hp:linesegarray` 캐시 제거 (glyph 뭉개짐 방지)
- W4. 새 폼/페이지/표 추가 요청은 writer가 거부하고 `hancom_com_worker` 큐로 라우팅
  (클라우드 백엔드에서 불가능한 작업임을 API 레벨에서 명시)
- W5. 산출물은 항상 새 파일 (원본 불변), draft 체인에 parent-hash 등록

## 2. 셀 레지스트리 (registry/) — "어디에·얼마나"의 단일 진실

양식(form_code)별 mutable cell 전수 등록. 사고 F2(옆 셀 날짜 누락)·F8(용량 초과)의 방지책.

```sql
CREATE TABLE cell_registry (
  cell_id        text PRIMARY KEY,   -- 예: QP-501-01.goal3.value
  form_code      text NOT NULL,
  anchor_before  text NOT NULL,      -- 유일 컨텍스트 문자열
  fill_class     text NOT NULL CHECK (fill_class IN
                   ('AUTO_STATIC','AUTO_DATE_ROLL','DATE_DERIVED',
                    'CONFIRM','NARRATIVE_SLOT','HUMAN_ONLY','NO_WRITE_HISTORY')),
  max_chars      int,
  verify_mode    text NOT NULL CHECK (verify_mode IN ('CONTAINMENT','EXACT_CELL_MATCH')),
  claim_type     text                -- LEGIT_HISTORY 등 (법규 제정일처럼 안 바뀌는 과거값)
);
```

완전성 게이트: run 종료 시 (a) 변경된 모든 텍스트 노드 ↔ 레지스트리 행 1:1 매핑,
(b) 값이 배정된 행 전부 적용됨. 하나라도 어긋나면 RUN FAILS. (허민 ×4 잔존 방지)

## 3. LLM 스키마 — 원안 보강

```python
class DraftField(BaseModel):
    field_id: str                      # cell_registry.cell_id와 FK
    content: str
    content_short: str | None = None   # 좁은 셀용 (≤16자). 모델이 즉석 축약 금지, 별도 슬롯
    source_ids: list[str]
    generation_type: Literal["source_extract","rule_transform","ai_draft","ai_inference"]
    requires_review: bool

class DocumentDraft(BaseModel):
    document_type: str
    target_year: int
    base_draft_sha256: str             # 어느 draft 위에 쓰는지 (체인 검증용)
    sections: list[DraftField]
    warnings: list[str]
```

주의: **모델의 `source_ids`는 주장일 뿐이다.** 검증 엔진이 실제 소스에서 containment 확인
(§6-V3). 인용 환각은 실제로 발생한다.

## 4. 필드 통제 게이트 (policy/) — 프롬프트가 아니라 코드로 차단

`requires_review=true`는 권고 표시일 뿐. 삽입 전 서버 강제:

- P1. `fill_class=HUMAN_ONLY` 셀에 `generation_type∈{ai_draft,ai_inference}` → **삽입 거부**,
  `[HUMAN_INPUT]` 마커 기록. (실적·심사결과·측정치·참석자·서명)
- P2. `fill_class=NO_WRITE_HISTORY` 셀은 값이 와도 무시 (법규 등록대장 제정일 등)
- P3. `AUTO_DATE_ROLL` 값은 날짜 파서 통과 필수 + §6-V4 의미검증 대상 태그
- P4. field_id가 레지스트리에 없으면 거부 (모델이 만든 유령 필드 차단)

## 5. RAG / File Search — 연도 오염 방지

- R1. 벡터 저장소는 **연도×문서타입 단위로 분리** (또는 metadata filter를 쿼리에 강제).
  2023~2026을 한 저장소에 넣으면 "비슷하지만 다른 연도" 값이 검색됨 — provenance 사고와 동계열.
- R2. 검색 결과는 값+출처(파일·페이지·셀)로 저장하고, 삽입 승인 전 원문 재확인 링크 제공.
- R3. 민감문서는 File Search 업로드 대신 자체 추출 텍스트만 최소 문맥으로 전달(원안의 혼합형).

## 6. 검증 엔진 (verifier/) — 쓰기 후, 독립 실행

핵심 원칙(프로젝트 최대 교훈): **작성기와 검증기는 같은 컨텍스트를 공유하지 않는다.**
검증기는 산출 파일 + 레지스트리 + 소스만 받는다 (작성기 로그·기대값 출력 금지).

- V1. **Round-trip**: 산출 HWPX에서 재추출 → 승인 JSON과 셀 단위 대조
  (verify_mode: CONTAINMENT=서술형, EXACT_CELL_MATCH=날짜·수치)
- V2. **잔재 스윕**: 금지 토큰 zero-count — 구 인명, 구 팀명, 이전 연도, 도메인 잔재어("식품").
  단 `claims` 파일에 신고된 LEGIT_HISTORY 값(법규 제정일 2023 등)은 제외. claims 없는 스윕은
  오탐으로 무력화된다 — 반드시 쌍으로 구현.
- V3. **인용 containment**: 각 source_id의 실제 원문에 content(또는 그 근거값)가 존재하는지.
- V4. **날짜 의미검증**: 유효기간=등록일+1년−1일, 종료일≥발생일, 검토일∈검토기간 등
  파생 규칙 assert. (실제 사고: 시작 전에 만료되는 자격 유효기간 F3)
- V5. **구조 게이트**: XML well-formed, style-ref 해소(charPr/paraPr/style/borderFill),
  manifest/spine/secCnt 정합, zip 순서.
- V6. **레지스트리 완전성** (§2).

## 7. 승인·이력 (audit/)

- A1. 승인 = run 폴더의 **결정 파일**(승인자·시각·draft sha256·셀 목록). UI 클릭 로그나
  채팅 승인은 무효 (R5). 결정 파일 없이 상태 승격 불가.
- A2. draft 계보: `parent_sha256` 체인. writer는 체인 head가 아닌 base 거부 (R3).
- A3. 사람 리뷰 단위 상한: 1회 1양식 또는 ≤20셀 (R11 — 93개 마커 중 사람이 잡은 건 1개였음).
- A4. run 레지스트리 테이블: run_id, script/prompt 버전, parent hash, 게이트 결과, 결정파일 경로.
- A5. LLM 호출 로그: 모델·프롬프트버전·토큰·비용·마스킹 여부 (원안 유지).

## 8. 보안 — 원안 + 실제 사고 반영

- 서버측 키, Secret Manager, `store=False`, 업로드 후 파일 삭제 (원안 유지)
- S1. **pre-commit secret scan** + 키 회전 절차 문서화 (이 repo의 미해결 사고 E10: 노출 키 미회전)
- S2. 문서 바이너리 git 금지: `*.hwp *.hwpx *.pdf *.doc* *.xls*` gitignore + pre-commit 훅 (R6)
- S3. LLM 전송 전 개인정보 마스킹은 gateway 단일 지점에서 (원안 유지, 위치만 고정)

## 9. 전처리 (ingest/) 추가 요건

- I1. HWP 바이너리(v5) 입력은 서버에서 직접 파싱하지 않음 → 업로드 요건 "HWPX/PDF로 변환 후
  업로드" 또는 `hancom_com_worker` 변환 큐 (실사례: 환경실적 2025.hwp)
- I2. 추출 산출물 = source_inventory: {값, 파일, 페이지/셀 위치, 연도 태그} — V3의 대조 기준
- I3. 표 추출은 HWPX zip+XML 직접 파싱 (미리보기 PrvText는 stale 캐시 — 신뢰 금지, 실사례 있음)

## 10. MVP 우선순위 (원안 10개 항목 재배열)

Phase 1 (이것 없이는 신뢰 불가): 셀 레지스트리 + writer(치환 전용) + V1/V5 게이트 + 결정파일
Phase 2: LLM gateway + Structured Outputs 초안 생성 + P1~P4 필드 통제 + V2/V3/V4
Phase 3: RAG(연도 분리) + 비교 UI + 비용 대시보드 + hancom_com_worker

> 원안과 가장 큰 차이: 원안은 "GPT 초안 생성"이 1번, 이 판은 **"안전하게 쓰고 검증하는 배관"이
> 1번**이다. 이 프로젝트에서 실패한 것은 모델 품질이 아니라 배관이었다.

## 11. 스택 (원안에서 변경분만)

| 항목 | 원안 | 수정판 |
|---|---|---|
| AI | OpenAI Responses API | 동일, 단 gateway를 provider-agnostic으로 (Claude 등 폴백/AB) |
| 문서 생성 | "DOCX/HWPX 템플릿 어댑터" | HWPX cell-writer(치환 전용) + Windows COM 워커 분리 |
| 검증 | 삽입 전 JSON 검사 | 삽입 후 round-trip + claims 기반 잔재 스윕 + 의미검증 |
| 승인 | 감사로그 | 결정파일 + parent-hash 체인 + 리뷰 ≤20셀 |
