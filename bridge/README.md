# Codex 헤드리스 통제 · 검토검열 · 수정보완 브리지

Claude(클라우드 세션 또는 로컬 헤드리스)가 **로컬 PC의 Codex와 한컴오피스를 원격 통제**하고,
Codex가 한 모든 작업을 **검토·검열한 뒤 수정·보완**해서 승인된 것만 반영하는 시스템.

```
 Claude (claude.ai 클라우드 세션)                  로컬 Windows PC
 ───────────────────────────────                 ─────────────────────────────────────────
 claude_bridge.py  codex/fix/apply/hancom   ──►   local_agent.py (git pull 폴링)
        ▲          (bridge/jobs/pending)    git      │
        │                                            ├─ Codex: worktree(codex/<id>)에서 실행
        │                                            ├─ audit.py: 비밀값 마스킹 + 정책검사
        │                                            ├─ 헤드리스 Claude 검토 (Opus/Sonnet 5.5 high)
        │                                            │     └ FIX → Claude(또는 Codex)가 수정보완 → 재검토
        │      bridge/jobs/done + bridge/reports  ◄──┤
        └── review / apply / discard / fix           ├─ Hancom COM: 변환·페이지수·InsertFile·텍스트
                                                     └─ harvest: ~/.codex/sessions 전체 수집·감사
```

전송 수단은 **이 git 저장소뿐**: PC는 바깥으로 git pull/push만 하므로 포트 개방, 터널, 원격데스크톱이
필요 없다. 원시 문서(hwp/hwpx/pdf)는 git에 올리지 않는다(R6). 결과로는 지표, 해시, 추출 텍스트만 올린다.

## 구성 파일

| 파일 | 위치 | 역할 |
|---|---|---|
| `local_agent.py` | PC | 작업 큐 폴링·실행, Codex 감독 루프, 세션 수집 |
| `supervisor.py` | PC | 모델 라우팅, 헤드리스 Claude 검토(`--json-schema`), 수정보완 |
| `audit.py` | 양쪽 | 비밀값 마스킹, 명령·경로·diff 정책 검사 → PASS / FLAG / BLOCK |
| `hancom_ops.py` | PC | 한글 COM (pywin32) |
| `jobqueue.py` | 양쪽 | git 기반 큐(pending → running → done) |
| `claude_bridge.py` | 클라우드 | 작업 제출·대기·검토·승인·폐기·로그 조회 CLI |
| `claude_profile/` | 전 프로젝트 | 모델 정책 배포(설정·CLAUDE.md·에이전트) |
| `MODS.md` | — | 이 프로젝트용 플러그인·스킬 수집 결과 |

## 모델 정책 (전 프로젝트)

- 일반 작업(문서, ISO 기록, 기획, 검토, Codex 감독): **`claude-opus-5-5`, effort `high`**
- 코딩 작업: **`claude-sonnet-5-5`, effort `high`**
- 코딩 여부는 **사용자의 표현이 아니라 Claude가 판단**한다(`supervisor.decide_coding`):
  작업의 `kind` → 실제로 바뀐 파일(코드 파일이 절반 이상이면 코딩) → 둘 다 없으면 Claude(Opus)가 요청을 읽고 판정
  → Claude 호출이 실패할 때만 키워드 규칙. 판정 근거는 결과의 `coding_source`에 남는다. 판정 결과는 각 보고서의 `model`/`effort`에 기록된다.
- 대화형 Claude Code에도 같은 정책을 적용하려면 다음을 실행한다.
  ```
  python bridge/claude_profile/install_profile.py --user          # 이 PC의 모든 프로젝트
  python bridge/claude_profile/install_profile.py --scan C:/work  # C:/work 아래 모든 git 저장소
  ```
  `settings.json`에는 `model` + `effortLevel`을 병합하고, `CLAUDE.md`에는 정책 블록을 추가한다.
  `coder` 에이전트(Sonnet 5.5 high)는 코딩 위임용, `codex-supervisor`(Opus 5.5 high)는 Codex 감독용이다.
  이 저장소(bio)에는 이미 적용했다.

## PC 설치 (Windows, 1회)

1. 필요 프로그램: Python 3.10+, git, [Codex CLI](https://github.com/openai/codex) (`npm i -g @openai/codex`, 로그인),
   Claude Code (`claude` 로그인), 한컴오피스 + `pip install pywin32`.
2. 이 저장소를 clone하고 작업 브랜치를 체크아웃한다. 원시 문서는 이 폴더에 그대로 두어도 된다(gitignore 처리됨).
3. `bridge/config.example.json`을 `bridge/config.json`으로 복사한 뒤 수정한다.
   - `branch`: 클라우드 Claude와 같은 브랜치
   - `projects`: Codex가 작업할 수 있는 **git 프로젝트** 목록(이름 → 경로). 목록에 없는 곳은 거부한다.
   - `review.fixer`: `claude`(Claude가 직접 수정) 또는 `codex`(검토 지시로 Codex 세션을 재개해 수정)
   - `review.auto_apply`: `true`이면 "검토 APPROVE + 감사 PASS"일 때 자동 병합한다. 기본값은 수동 승인.
4. Codex CLI 버전에 따라 플래그가 다를 수 있으므로 `codex exec --help`로 확인한 뒤
   `codex_exec_cmd`/`codex_resume_cmd` 템플릿을 맞춘다(기본값은 `--json`, `--full-auto`,
   `--output-last-message`, 프롬프트는 stdin `-`).
5. 한글 보안 팝업 제거: 한컴 개발자센터의 `FilePathCheckerModule.dll`을 등록한다
   (`HKCU\Software\HNC\HwpAutomation\Modules`의 문자열 값 `FilePathCheckerModule` = dll 경로).
6. `bridge\start_agent.bat`을 실행한다(작업 스케줄러에 "로그온 시 실행"으로 등록 권장).
   클라우드에서 `ping` 작업으로 연결을 확인한다.

## 사용 (클라우드 Claude 쪽)

```bash
python bridge/claude_bridge.py ping --wait
python bridge/claude_bridge.py codex my-app "로그인 API에 rate limit 추가" --kind code --wait
python bridge/claude_bridge.py review <job_id>        # diff·감사(재실행)·로컬 검토 결과
python bridge/claude_bridge.py fix <job_id> "auth.py 42행: 예외 시 카운터 롤백 누락. 테스트 추가" --wait
python bridge/claude_bridge.py apply <job_id> --wait  # 승인 → 원 프로젝트에 --no-ff 병합
python bridge/claude_bridge.py discard <job_id> --reason "방향 틀림"
python bridge/claude_bridge.py hancom page_count --src 품질실적모음_2026년.hwpx --wait
python bridge/claude_bridge.py logs --flagged         # 사람이 직접 돌린 Codex 세션까지 전 프로젝트 감사
python bridge/claude_bridge.py status
```

### Codex 작업 생명주기

1. `codex.exec`: 원 프로젝트 HEAD에서 `codex/<job_id>` 브랜치 worktree를 만들고 그 안에서 Codex를 실행한다.
   원본 작업트리는 건드리지 않는다.
2. 이벤트(JSONL)와 diff를 **비밀값 마스킹** 후 `bridge/reports/<job_id>/`에 저장하고 `audit.json`을 생성한다.
3. 헤드리스 Claude가 검토해 APPROVE / FIX / REJECT 중 하나로 판정한다. FIX이면 수정보완 후 재감사·재검토하며,
   이를 최대 `max_fix_rounds`회 반복한다. 모든 라운드는 `review_N.json`, `fix_N.json`으로 남는다.
4. 결과 상태: `approved` / `needs_review` / `rejected` / `blocked`(감사 BLOCK) / `codex_failed`.
5. 클라우드 Claude(`codex-supervisor`)가 `review`로 다시 검열한 뒤 `apply` / `fix` / `discard`를 결정한다.
   BLOCK은 `--override "<사유>"` 없이는 병합하지 않는다.

### 감사 규칙 (audit.py)

- **BLOCK**: 루트/드라이브 삭제, 포맷, `curl | sh`, force push, 레지스트리·실행정책·백신 변경,
  자격증명 파일 접근, 스케줄러 등록, 원시 문서·비밀 파일 커밋, `.git` 내부 수정,
  추가된 줄에 비밀값 포함, TLS 검증 해제.
- **FLAG**: 히스토리 재작성, Codex 단독 push, 패키지 설치, 네트워크, sudo, CI·hook·`.gitignore`·bridge 자체 수정,
  raw HWPX XML 작성, 테스트 비활성화, eval/shell=True, 로그에 비밀값 노출.
- 규칙은 `COMMAND_RULES` / `PATH_RULES` / `DIFF_RULES`에 정규식 한 줄씩 추가해 확장한다.

## 주의

- 이 저장소에 올라가는 로그와 diff는 마스킹을 거치지만 **원문 작업 내용은 남는다**.
  저장소는 비공개로 유지할 것.
- 작업을 push할 수 있는 사람은 PC에서 Codex를 실행시킬 수 있다. 저장소 쓰기 권한을 최소화할 것.
  `shell.run`은 기본적으로 꺼져 있고, 켜더라도 `shell.allow`에 등록된 실행 파일만 허용한다.
- 테스트: `python -m unittest discover -s bridge/tests -v`
  (가짜 codex/claude 실행 파일로 제출 → 실행 → 검토 → 수정 → 재검토 → 병합 → 수집 전 과정을 검증한다).
