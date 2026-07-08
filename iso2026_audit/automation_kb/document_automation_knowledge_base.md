# 문서 자동화 시스템 지식베이스 (Document Automation Knowledge Base)

두 세션(document review / document review continuation)의 전 과정에서 검증된
작업 절차·코딩 패턴·콘텐츠 추론 방법의 총정리.
**목표: 하위(저성능) 모델도 이 문서만 따르면 동일 품질의 결과를 재현하는 것.**
핵심 설계 사상: *판단을 체크리스트와 assert로 변환한다. 자유 생성을 금지하고 측정을 강제한다.*

---

## 1. 시스템 개요

자동화 대상: 연 1회 ISO 9001/14001 실적 문서 패키지의 연도 롤포워드
(전년 패키지 → 당해년 패키지: 날짜/인명/조직/실적/심사결과 갱신 + 신규 폼 기입).

| 실행 계층 | 담당 | 가능 작업 |
|---|---|---|
| 클라우드 (모델+Python) | 텍스트 레벨 XML 편집 | 셀 텍스트 치환·기입, 검증 게이트, 패키징 |
| Windows Hancom COM | 구조 작업 | 폼 삽입(InsertFile), 구역 분리, 페이지 복제 |
| 운영자 (인간) | 사실·승인·최종 검증 | 비즈니스 사실 제공, draft 승인, **Hancom 열림 확인**, 시각 검토 |

**운영자-크롭 패턴 (검증된 우회로):** 구조 작업(폼 추출)이 필요할 때 운영자가
Hancom에서 해당 폼만 잘라 별도 HWPX로 저장해 주면, 클라우드 작업이 전부
안전한 텍스트-레벨 기입으로 축소된다. (통보서 3건이 이 패턴으로 성공.
크로스-도큐먼트 XML 이식은 crash 검증됨 → 절대 금지.)

---

## 2. 작업 절차 시퀀스 (Job Procedure Sequence)

모든 작업은 이 11단계를 순서대로 통과한다. 단계 생략 금지.

```
1 INVENTORY   파일 전수 조사. 베이스/도너 식별.
              ⚠ 파일명·타 문서의 주장을 믿지 말고 내용 프로브로 계보 확인
              (사례: "V6"라던 업로드본이 실제로는 pre-V5였음 — 마커 문자열 존재
               여부를 grep으로 직접 확인해서 발견)
2 FACT TABLE  확정 비즈니스 사실을 단일 권위 문서(SESSION_MASTER_INDEX)로 수집.
              모든 기입값은 이 표 또는 도너 또는 운영자 지시로 추적 가능해야 함.
3 SURVEY      실제 베이스 파일에서 결함 클래스 전수 측정 (오탈자/조직명/연도잔재/
              dangling ref/캐시). 결과는 "패턴: 개수" 표로 기록.
4 DECISION    운영자 결정을 날짜 붙은 지시 문서로 기록. 충돌 시 최신 우선.
              폐기된 권고는 "폐기" 명시 (조용히 덮어쓰지 않음).
5 SPEC        편집 전에 기입 사양 작성: (위치앵커, 이전값, 새값, 근거출처, 예상횟수).
              하위 모델은 이 표의 행을 기계적으로 실행만 하면 되는 상태로 만든다.
6 EDIT        count-assert 치환만 실행 (안전클래스 §3). 하나라도 불일치 → 전체 중단,
              부분 저장 금지.
7 GATE        검증 스위트: XML well-formed / style-ref 0 dangling / 필수문자열 /
              잔재 0건 / CRC.
8 PACKAGE     archive-clone 패키징 (§4.1). zip -r 재압축 절대 금지.
9 VERIFY      산출물에서 텍스트 재추출 → 변경 영역 diff 열거 → 변경범위 == 의도범위 확인.
10 DELIVER    운영자가 Hancom에서 열림 확인 (클라우드에서 불가능한 유일한 게이트).
11 RECORD     빌드 기록 문서 + 원장(ledger) 상태 갱신 + commit/push.
              채팅 기억이 아니라 저장소가 상태 저장소다.
```

---

## 3. 조작 안전 클래스 (Operation Safety Classes)

| 클래스 | 조작 | 위험도 | 실행 장소 |
|---|---|---|---|
| A | 기존 셀의 빈 run에 텍스트 기입 / 기존 텍스트 치환 | 안전 | 클라우드 |
| B | 셀 내 문단 교체 (문단 수·구조 유지) | 안전 | 클라우드 |
| C | 동일 파일 내 폼/행 복제 (FORM_DUPLICATE) | 주의 (선례 있음) | 클라우드, 선언 필수 |
| D | 크로스-도큐먼트 삽입, 구역 분리/병합 | **crash 검증됨** | Hancom COM 전용 |
| E | 표 크기/구조 변경 | 원칙 금지 | geometry policy 사다리 참조 |

D가 필요하면 → 운영자-크롭 패턴으로 A로 변환하는 것이 최우선 전략.
E가 유혹될 때(텍스트가 안 들어감) → **표를 늘리지 말고 텍스트를 줄인다** (§5.8).

---

## 4. 코딩 시스템 (HWPX Manipulation Patterns)

실전에서 파일을 깨뜨렸거나 살린 패턴들. 각 항목에 "왜"가 붙어 있다 —
하위 모델은 왜를 무시하고 패턴만 정확히 복사해도 된다.

### 4.1 패키징: archive-clone (R-PKG-1) — 가장 중요한 규칙
HWPX는 zip이지만 **읽는 쪽이 관용적이지 않다.**
실패 사례: `zip -r`로 재압축 → 디렉터리 엔트리 3개 생성 + 엔트리 순서 변경
→ Hancom "파일이 손상되었습니다".
**규칙: 절대 폴더를 재압축하지 않는다. 원본 아카이브를 엔트리 단위로 복제하면서
편집한 파일의 바이트만 교체한다.**
```python
zin = zipfile.ZipFile(SRC); zout = zipfile.ZipFile(OUT, "w")
for item in zin.infolist():                      # 원본 순서 그대로
    data = edited.get(item.filename) or zin.read(item.filename)
    ni = zipfile.ZipInfo(item.filename, date_time=item.date_time)
    ni.compress_type = item.compress_type        # mimetype=STORED 자동 보존
    ni.external_attr = item.external_attr; ni.internal_attr = item.internal_attr
    ni.create_system = item.create_system
    zout.writestr(ni, data)
```
검증: 엔트리 수/순서 원본과 동일, 디렉터리 엔트리 0, mimetype 선두+STORED, flag bits 0.
(도구: `tools/hwpx_repack.py`)

### 4.2 텍스트 모델과 추출기
구조: `hs:sec > hp:p > hp:run > hp:t`. 표 셀 안 문단은 `hp:tc > hp:subList > hp:p`로 중첩.
**함정: `<hp:t>`에 속성이 붙을 수 있고, 내부에 태그가 중첩될 수 있다.**
`<hp:t>([^<]*)</hp:t>`만 쓰면 일부 텍스트를 놓쳐 "수정 안 됐다"는 오판을 낳는다(실제 발생).
```python
ts = re.findall(r'<hp:t[^>]*>(.*?)</hp:t>', p, re.S)   # 속성 허용
txt = ''.join(re.sub(r'<[^>]+>', '', t) for t in ts)   # 중첩 태그 제거
```
(도구: `tools/hwpx_textdump.py`)

### 4.3 최상위 문단 인덱싱 (깊이 추적)
셀 안에도 `<hp:p>`가 있으므로 naive split은 경계를 틀린다. 폼의 범위를 잡을 때는
깊이 카운터로 **hs:sec 직계 문단**만 인덱싱한다:
```python
depth=0; tops=[]
for m in re.finditer(r'<hp:p [^>]*>|</hp:p>', data):
    if m.group(0).startswith('</'):
        depth-=1
        if depth==0: tops.append((cur, m.end()))
    else:
        if depth==0: cur=m.start()
        depth+=1
```

### 4.4 셀 그리드 주소화 기입 (폼 채우기의 표준형)
폼 기입은 "라벨 다음 셀" 추측이 아니라 **(row,col) 주소 지도**로 한다:
```python
for m in re.finditer(r'<hp:tc [^>]*>', doc):
    a=m.start(); b=doc.find('</hp:tc>',a)+8
    ad=re.search(r'colAddr="(\d+)" rowAddr="(\d+)"', doc[a:b])
    spans[(int(ad.group(2)), int(ad.group(1)))]=(a,b)
```
빈 셀의 표준 패턴은 `<hp:run charPrIDRef="N"/>` (self-closing).
기입 = 같은 charPr를 재사용해 `<hp:run charPrIDRef="N"><hp:t>값</hp:t></hp:run>`으로 교체.
**여러 셀을 채울 때는 문서 뒤쪽부터(오프셋 내림차순) 적용해야 span이 안 깨진다.**
멀티라인 필드(부적합사항 등)는 보통 "행마다 셀 하나" 구조 → 줄을 나눠 연속 행 셀에 기입.
(도구: `tools/hwpx_cellfill.py`)

### 4.5 count-assert 치환 엔진 (코드 정확도의 핵심)
```python
def rep(s, old, new, expect, label):
    n = s.count(old)
    if n != expect: fails.append(f"{label}: expected {expect}, found {n}"); return s
    return s.replace(old, new)
# ... 모든 치환 후:
if fails: print("ABORT", fails); sys.exit(1)   # 부분 저장 절대 금지
```
- 예상 횟수는 **사전 SURVEY에서 측정한 값**을 쓴다. 추측 금지.
- ABORT가 나면 expect를 늘려 통과시키지 말고 **원인을 조사**한다.
  (사례: lineseg expect 1 → 실제 139. 원인은 `grep -c`가 줄 수를 세는데
  XML이 한 줄로 minify되어 있었던 것. 조사가 진짜 버그를 찾았다.)

### 4.6 모호한 대상의 위치 지정 (anchored positional edit)
같은 패턴이 여러 곳에 있으면(빈 목표 슬롯 3/4/5처럼) 전역 치환 금지.
앵커 두 개 사이 구간을 slice → 그 안에서 1회 치환 → 재조립:
```python
i3=s.find("목표달성 항목 3"); i4=s.find("목표달성 항목 4")
seg=s[i3:i4]; assert seg.count(EMPTY)==1
s=s[:i3]+seg.replace(EMPTY, FILLED, 1)+s[i4:]
```

### 4.7 linesegarray (레이아웃 캐시)
편집된 문단의 stale 캐시는 글자 뭉개짐(mash)을 만든다. **편집한 섹션에서는 전부 제거**
(뷰어가 재계산): `re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>','',s,flags=re.S)`

### 4.8 style-ref 게이트 (crash 방지)
헤더에 정의 안 된 charPrIDRef/paraPrIDRef/styleIDRef/borderFillIDRef = Hancom crash 위험.
편집 후 반드시: 헤더에서 정의 id 집합 추출 → 섹션의 사용 id와 차집합 = 0 확인.
발견 시 알려진 안전 id로 재매핑 (사례: 191/193 → 19).
새 스타일을 만들지 않는 것이 원칙 — **항상 파일 안에 이미 있는 id만 재사용.**

### 4.9 XML 이스케이프
`&` = `&amp;` (조직명 "제품생산&연구개발팀"). 검증 시에는 양쪽을 unescape해서 비교.

### 4.10 용량 규칙 (R-CAPACITY)
새 텍스트는 원문 대비 ~1.3배 이내. 셀 폭(HWPU)÷1100 ≈ 한글 글자수/줄.
넘치면 표를 늘리지 말고 문안을 단축 (마스터 인덱스의 요약 문형 활용).

### 4.11 검증 배터리 (모든 산출물 공통)
```
□ XML well-formed (전 파트)          □ style-ref dangling 0
□ 필수 문자열 존재 (기입값 전수)      □ 잔재 문자열 0 (이전값·연도·오탈자)
□ zip CRC / 엔트리 순서·수 원본 동일  □ 변경영역 diff 열거 → 의도범위와 대조
□ PrvText.txt 연도 잔재 확인          □ (운영자) Hancom 열림 + 시각 검토
```

---

## 5. 콘텐츠 추론 방법 (내용을 "말이 되게" 만드는 사고 절차)

### 5.1 무추론 원칙 (zero-inference)
모든 기입값의 출처는 셋 중 하나: ① 확정 사실 표 ② 도너 문서 ③ 운영자 명시 입력.
셋 다 없으면 값을 만들지 말고 `[HUMAN_INPUT]` 마커를 남긴다.
"그럴듯한 값"을 지어내는 순간 외부심사 리스크가 된다.

### 5.2 도너 관례 > 직관
형식이 애매하면(날짜 체계, 표기법, 문체) **전년 문서가 어떻게 했는지 찾아 복사**한다.
사례: 통보서의 발행일=조치요구일=조치일 동일 날짜가 "비현실적"으로 보였지만
2024 도너의 관례였음 → 유지가 정답. 직관으로 "개선"하면 오히려 불일치가 생긴다.

### 5.3 추적 사슬 (traceability chain)
내용은 문서를 가로지르는 인과 서사를 이뤄야 한다:
```
심사 finding → 통보서 부적합사항(1:1 전사) → 시정조치 → 신규 목표 →
실천계획서 → 경영검토서 세부내용
```
규칙: **같은 사실 = 모든 위치에서 동일 문안** (목표 문안은 글자 단위 동일).
새 사실을 한 곳에 넣으면 → 그 사실이 등장해야 할 전 위치의 전파 지도를 먼저 만든다.

### 5.4 진화, 반복 금지 (evolution not repetition)
연차 결과물은 전년과 달라야 한다. 검증된 문형:
"X는 실시/정비되었으나, (새로운 단계의) Y가 미흡/지연/누락됨."
— 전년 지적이 해결된 흔적 + 당해년의 새 문제. 3년 동일 문안 = 외부심사 지적 위험.

### 5.5 시간 정합성
날짜는 인과 순서를 지켜야 한다 (검토일 3월 vs 심사일 6월 역설 같은 것을 발견하면
바로 고치지 말고 **도너의 관례를 확인**하고, 관례가 같은 모순을 갖고 있으면 운영자에 질문).
연도 롤 규칙: "전년 값에서 연도만 +1, 월·일 동일" (기간 폭 확장이 아님 — 실제 오해 사례 있음).

### 5.6 결정 권한 분리
모델이 정하는 것: 형식, 전파, 정합성, 문안 단축.
운영자만 정하는 것: 목표 문안 승인, draft(원인분석/조치내용) 확정, 실명 기재 여부,
실측값, 범위 결정(어느 문서를 닫을지).
→ 헷갈리면 "이 값이 틀렸을 때 외부심사에서 누가 책임지는가"로 판단.

### 5.7 목표 규칙
연도별 목표 변경은 **1개 수정 또는 1개 추가** 중 하나만. 기존 문안은 무수정 유지.

### 5.8 긍정 응답 문서(설문 등)의 신뢰성 규칙
전항목 만점 금지 — 1개 항목은 "보통"으로 남겨 신뢰성 확보 (운영자 정책).
자유기술은 과학적 구체성으로: 제품 로트 균일성/재현성/납기 같은 실제 연구 맥락 언어 사용.

---

## 6. 하위 모델 실행 프로토콜 (낮은 모델로 좋은 결과 내는 법)

핵심: **판단을 없애고 측정과 실행만 남긴다.**

### 6.1 믿지 말고 측정하라
- 파일 상태에 대한 모든 주장(파일명, 이전 보고서, 자신의 기억)은 프로브로 재확인.
- 편집 전: 대상 문자열의 실제 바이트를 출력해서 본 다음 그 바이트에 대고 편집을 작성.
  기억 속 구조에 대고 코드를 쓰지 않는다.
- 편집 후: 재추출 → diff → 변경 영역 수와 내용을 열거 → 의도와 1:1 대조.

### 6.2 턴당 하나의 산출물
큰 요청을 한 턴에 다 하려 하면 품질이 붕괴한다. 순서를 정하고 하나씩:
조사 턴 → 사양 턴 → 실행 턴 → 검증 턴. 각 턴의 끝은 항상 검증 가능한 상태.

### 6.3 assert-first 코딩
실행 전에 기대값을 코드에 박는다 (§4.5). 기대와 다르면 멈춘다.
**assert를 통과시키기 위해 기대값을 고치는 것은 조사 후에만 허용**
— "왜 139인가?"를 설명할 수 있을 때.

### 6.4 앵커-확인-편집 루프 (편집 사이트당 반복)
```
1 앵커 문자열로 위치 탐색 → 2 주변 raw XML 300-500자 출력 →
3 실제 구조 확인 (run 분할, charPr, 문단 수) → 4 그 구조에 맞는 치환 작성 →
5 예상 횟수 기록 → 6 실행은 전체 일괄 (부분 실행 금지)
```

### 6.5 사양 표 실행 (하위 모델용 인터페이스)
상위 판단자가 만든 사양 표의 형식:
```
| 위치앵커 | 이전값(정확한 바이트) | 새값 | 출처 | 예상횟수 |
```
하위 모델은 표를 코드로 옮기고 실행만 한다. 값을 바꾸거나 "개선"하지 않는다.
새값이 셀 용량을 넘으면 실행하지 말고 단축안을 제시하고 승인 대기.

### 6.6 중단 트리거 (즉시 STOP하고 질문/플래그)
- count 불일치 / 예상 구조와 실제 구조 불일치
- 기입값의 출처 부재 (§5.1)
- Class D/E 조작이 필요해 보일 때
- 같은 파일에 대해 두 문서가 상반된 상태를 주장할 때 (모순 기록 후 질문)

### 6.7 상태는 저장소에 (bootstrapping)
새 세션은 반드시 이 순서로 읽는다:
`SESSION_MASTER_INDEX.md` (사실) → `iso2026_completion_ledger.csv` (진행 상태)
→ 최신 날짜의 검토세션/지시 문서 (결정) → 관련 빌드 기록 (직전 작업).
채팅 기록은 유실된다 — 결정·사실·상태를 항상 저장소 문서로 남기고 커밋한다.

### 6.8 실패 보고의 정직성
게이트 실패, 부분 완료, 검증 불가(예: 클라우드에서 Hancom 열림 확인 불가)는
그대로 보고한다. "아마 될 것"이라고 말하지 않는다. 검증 못 한 것은 운영자 게이트로 넘긴다.

---

## 7. 실패 사례 카탈로그 (증상 → 근본원인 → 예방규칙)

| # | 증상 | 근본원인 | 예방규칙 |
|---|---|---|---|
| 1 | "파일이 손상되었습니다" | zip -r 재압축: 디렉터리 엔트리+순서 변경 | R-PKG-1 archive-clone (§4.1) |
| 2 | Hancom crash | 크로스-도큐먼트 삽입의 dangling style-ref | Class D 금지, style-ref 게이트 (§4.8) |
| 3 | 글자 뭉개짐(mash) | 편집 문단의 stale linesegarray | 편집 섹션 캐시 전제거 (§4.7) |
| 4 | "이미 수정됨" 오판 | 추출기가 속성 있는 hp:t 누락 | 강건 추출기 (§4.2) + 2중 확인 |
| 5 | 잘못된 베이스에 작업 | 파일명/보고서 신뢰 | 계보 프로브 (§2-1) |
| 6 | assert 대량 불일치 | grep -c는 줄 수 (minified XML) | 발생 횟수는 프로그램으로 계수 (§4.5) |
| 7 | 연도 잔재 | 맹목 캐리 (본문·PrvText·개정번호) | 잔재 sweep 목록 + 프리뷰 확인 |
| 8 | 문서 간 사실 불일치 | 다중 위치 사실을 한 곳만 수정 | 사실별 전파 지도 (§5.3) |
| 9 | 셀 넘침/표 변형 | 긴 문안을 그대로 기입 | R-CAPACITY 단축 (§4.10) |
| 10 | 3개년 동일 문안 | 전년 복사 | 진화 문형 (§5.4) |

---

## 8. 재사용 자산 색인

### 도구 (이 폴더 tools/)
- `hwpx_textdump.py` — HWPX→텍스트 (강건 추출기, 계보 프로브·검증용)
- `hwpx_repack.py` — archive-clone 패키징 + 구조 검증
- `hwpx_cellfill.py` — 셀 그리드 주소화 기입 엔진 (빈 run 채움, count-assert)

### 정책/사양 (temporal_analysis_20260703/)
- `yearly_rollforward_automation_spec.md` — 무추론 연도 롤포워드 파이프라인
- `iso2026_build_procedure_no_freedom.md` — 제로-자유도 빌드 절차
- `table_geometry_change_policy.md` — 표 크기 변경 결정 사다리 (Class E)
- `content_fill_directive_layout_frozen.md` — 레이아웃 동결 채움
- `b7_통보서_content_and_form_addition_spec.md` / `b9_form_content_spec_2026.md`
- `history_review_rules_and_subagents_20260703.md` — 규칙+서브에이전트 아키텍처

### 상태 (temporal_analysis_20260703/)
- `SESSION_MASTER_INDEX.md` — 사실 권위 / `iso2026_completion_ledger.csv` — 진행 상태 기계
- `품질심사_2026_검토세션_20260708.md` — 결정 기록 양식의 예
- `품질심사_2026_V7_build_20260708.md` — 빌드 기록 양식의 예

### 검증된 산출물 (재현 가능한 실행 사례)
- V7 빌드: 49개 텍스트 치환 + 캐시/참조 수리 (검토세션 지시 전체 적용)
- 통보서 3건: 운영자-크롭 폼 → 셀 그리드 기입 → 3파일 (Task 완료 사례)
