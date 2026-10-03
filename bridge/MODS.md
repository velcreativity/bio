# 프로젝트 관련 mods 수집 (2026-10-03)

대상 프로젝트: **Codex 헤드리스 통제·검토검열·수정보완 브리지** + **바이오프렌즈 ISO 2026 HWPX 자동화**.
수집 경로: claude.ai 플러그인 카탈로그(Anthropic Directory), 세션 내장 스킬, MCP 레지스트리.

## 1. 채택 후보 플러그인 (Anthropic Directory, 미설치)

| 플러그인 | 게시자 | 역할(이 프로젝트에서) | 권장 |
|---|---|---|---|
| Codex Dispatch | community | Codex를 MCP로 호출 — cwd·sandbox 강제, 자기완결 프롬프트. 브리지의 `codex.exec`과 같은 역할을 대화형 세션에서 수행 | ★ 설치 |
| codex-review | community | Claude↔Codex 계획 왕복 리뷰(Codex 승인까지 반복) | 선택 |
| code-review | **Anthropic** | PR/diff 다중 에이전트 리뷰 + 신뢰도 점수 → Codex diff 2차 검열 | ★ 설치 |
| claude-code-review-council | community | 6개 전문 리뷰어(정확성·보안·정책/신뢰경계·테스트증거·아키텍처·인터페이스) + PreToolUse hook | ★ 설치(검열 핵심) |
| finecomb | community | 전수 코드리뷰·보안감사 체크리스트(읽기 전용) | 선택(보안 심층) |
| PWP / drillspark / arn-code | community | 범용 워크플로·CVE 스캔 | 보류(범위 과다) |

설치: claude.ai → Settings → Plugins (또는 이 세션에 표시된 설치 카드). 설치 후 로컬 PC에서
`claude plugin list`로 확인.

## 2. 이미 사용 가능한 내장 스킬

- `/security-review` — 브랜치 변경분 보안 검토 (Codex 브랜치 승인 전 실행)
- `/code-review` — diff 정확성 리뷰 (`--fix`로 수정 적용)
- `plugin-authoring` — 자체 mod(hook·status line) 제작: Codex 감사 결과를 상태줄/토스트로 표시하는 mod의 기반
- `session-start-hook` — 클라우드 세션 시작 시 브리지 의존성 준비

## 3. MCP 커넥터

- MCP 레지스트리 검색은 **커넥터 제안 옵트인이 꺼져 있어** 결과 없음 →
  Claude 설정에서 connector suggestions를 켜면 Windows/데스크톱 제어용 커넥터 재검색 가능.
- Codex 자체도 MCP 서버로 동작(`codex mcp-server`) — 로컬 Claude Code에
  `claude mcp add codex -- codex mcp-server` 로 붙이면 대화형 통제도 가능.
  (헤드리스·감사 경로는 본 브리지의 `codex exec --json` 사용)

## 4. HWP/Hancom 관련

- 카탈로그에 HWP/HWPX 전용 mod 없음 → 본 저장소의 `bridge/hancom_ops.py`(pywin32 COM)로 자체 구현.
