<!-- codex-bridge model policy: BEGIN (managed by bridge/claude_profile/install_profile.py) -->
## 모델 정책 (모든 프로젝트 공통)

- **일반 작업**(문서·ISO 기록·기획·조사·검토·Codex 감독): **Opus 5.5, effort high** — 세션 기본값.
- **코딩 작업**(코드 작성·수정·리팩터·테스트·빌드·디버깅): **Sonnet 5.5, effort high** —
  직접 코딩하지 말고 `coder` 서브에이전트에 위임한다. 코드 리뷰도 `coder`가 아니라
  `codex-supervisor`(Opus)가 판단하되, 코드 diff 정밀 검토는 `coder`에 맡겨도 된다.
- Codex 작업의 검토·검열·수정보완은 `codex-supervisor` 에이전트와
  `bridge/claude_bridge.py`(있을 경우)로 수행한다. Codex 결과는 리뷰 없이 병합하지 않는다.
- 헤드리스 실행 시: 일반 `claude -p --model claude-opus-5-5 --effort high`,
  코딩 `claude -p --model claude-sonnet-5-5 --effort high`.
<!-- codex-bridge model policy: END -->
