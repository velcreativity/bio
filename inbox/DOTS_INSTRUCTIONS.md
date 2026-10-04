# Dots에게 붙여넣을 지시문

아래 블록 전체를 ChatGPT Dot에게 그대로 보낸다. (사전 준비: ChatGPT에서 이 Dot에 **GitHub 앱 연결** →
`velcreativity/bio` 저장소 접근 허용)

```
앞으로 나에게 결과물을 줄 때, Claude도 받아볼 수 있도록 GitHub에도 올려줘. 이건 계속 지켜야 하는 작업 규칙이야.

[어디에]
- 저장소: velcreativity/bio
- 브랜치: claude/charming-einstein-ds96tj  (이 브랜치에만. main이나 다른 브랜치 금지)
- 폴더: inbox/  (이 폴더 밖의 파일은 절대 수정·삭제하지 마)

[어떻게]
- 파일 이름: YYYYMMDD-HHMM_dots_주제.확장자  (한국 시간 기준)
- 글은 .md, 표는 .csv(UTF-8), 데이터는 .json, 이미지는 .png
- .md 파일 맨 위에 이 머리말을 넣어:
  ---
  from: dots
  title: (한 줄 제목)
  created: (ISO 날짜시간, +09:00)
  request: (Claude가 이 자료로 해 줬으면 하는 일, 없으면 생략)
  related_files: (같이 올린 파일 이름들, 없으면 생략)
  ---
- 커밋 메시지: "inbox: dots (주제)"
- 일반 커밋만. force push 금지.

[하지 말 것]
- 비밀번호, API 키, 토큰, 주민번호 같은 개인정보는 넣지 마.
- .hwp .hwpx .pdf .docx .xlsx .zip 파일은 올리지 마. 필요하면 내용을 .md나 .csv로 옮겨서 올려.
- 한 파일 20MB 넘기지 마.

[끝나면]
- 올린 파일 이름과 커밋 링크를 나에게 알려줘.
- GitHub에 접근이 안 되면 억지로 다른 방법 쓰지 말고 안 된다고 알려줘.

먼저 테스트로 inbox/ 에 "20261004-0000_dots_연결테스트.md" 파일을 하나 올려서 연결을 확인해줘.
내용은 머리말 + "연결 테스트입니다." 한 줄이면 돼.
```
