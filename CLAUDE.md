<!-- codex-bridge model policy: BEGIN (managed by bridge/claude_profile/install_profile.py) -->
## 모델 정책 (모든 프로젝트 공통)

- **일반 작업**(문서·ISO 기록·기획·조사·검토·Codex 감독): **Opus 5.5, effort high** — 세션 기본값.
- **코딩 작업**(코드 작성·수정·리팩터·테스트·빌드·디버깅): **Sonnet 5.5, effort high** —
  직접 코딩하지 말고 `coder` 서브에이전트에 위임한다. 코드 리뷰도 `coder`가 아니라
  `codex-supervisor`(Opus)가 판단하되, 코드 diff 정밀 검토는 `coder`에 맡겨도 된다.
- **코딩 여부는 Claude가 스스로 판단한다.** 사용자는 "코드 써줘"라고 말하지 않는다(기술 용어를 쓰지 않음).
  요청을 끝내기 위해 프로그램 코드를 작성·수정해야 한다고 판단되면, 사용자에게 묻지 말고 그 부분을
  즉시 `coder`(Sonnet 5.5 high)에 위임한다. 위임했다면 답변에 한 줄로 알린다.
- 판단 기준은 **결과물이 코드인가**다. 영상·콘텐츠 작업의 기획·대본(스크립트)·콘티·툴용 프롬프트 작성은
  일반 작업(Opus)이고, 영상 툴 API 호출·ffmpeg 편집·대량 생성·자동화 파이프라인 코드 작성은 코딩(Sonnet)이다.
  한 요청에 둘이 섞이면 기획은 직접, 코드 부분만 `coder`에 위임한다.
- Codex 작업의 검토·검열·수정보완은 `codex-supervisor` 에이전트와
  `bridge/claude_bridge.py`(있을 경우)로 수행한다. Codex 결과는 리뷰 없이 병합하지 않는다.
- 헤드리스 실행 시: 일반 `claude -p --model claude-opus-5-5 --effort high`,
  코딩 `claude -p --model claude-sonnet-5-5 --effort high`.
<!-- codex-bridge model policy: END -->
