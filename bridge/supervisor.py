"""Headless Claude supervision of Codex work: model routing, review, fix/improve.

Model policy (user rule, applies to every project):
  - coding work  -> claude-sonnet-5-5, effort high
  - everything else (documents, ISO records, planning, review of non-code) -> claude-opus-5-5, effort high
"""
import json
import os
import re
import subprocess

DEFAULT_MODELS = {
    "general": "claude-opus-5-5",
    "coding": "claude-sonnet-5-5",
    "effort": "high",
}

CODE_EXT = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".php", ".swift", ".m", ".scala",
    ".sh", ".bash", ".ps1", ".bat", ".cmd", ".sql", ".html", ".css", ".scss", ".vue",
    ".svelte", ".lua", ".r", ".dart", ".toml", ".yaml", ".yml", ".gradle", ".ipynb",
}
CODE_WORDS = re.compile(
    r"(?i)\b(code|coding|bug|refactor|test|function|class|script|api|build|compile|deploy|"
    r"lint|python|javascript|typescript)\b|코드|코딩|버그|리팩터|테스트|함수|스크립트|빌드|배포"
)


def is_coding(paths=(), prompt="", kind=None):
    """kind ('code'|'general') wins; else changed paths; else prompt keywords."""
    if kind in ("code", "coding"):
        return True
    if kind == "general":
        return False
    paths = list(paths)
    if paths:
        code = sum(1 for p in paths if os.path.splitext(p)[1].lower() in CODE_EXT)
        return code * 2 >= len(paths)
    return bool(CODE_WORDS.search(prompt or ""))


def pick_model(models, coding):
    m = dict(DEFAULT_MODELS, **(models or {}))
    return (m["coding"] if coding else m["general"]), m["effort"]


# ------------------------------------------------------------------- review

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["APPROVE", "FIX", "REJECT"]},
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "fix_instructions": {"type": "string"},
    },
    "required": ["decision", "summary", "issues", "fix_instructions"],
}

REVIEW_PROMPT = """너는 Codex 작업의 검토·검열 담당이다. 아래 Codex 작업 보고서를 검토하라.

판단 기준(순서대로):
1. 요청(task) 충족 여부 — 빠진 요구, 잘못 이해한 요구.
2. 정확성 — 버그, 경계조건, 깨진 테스트, 잘못된 데이터/연도/이름(문서 작업이면 연도 잔재·이름 교체 누락).
3. 프로젝트 규칙 위반 — 자동 감사(audit) findings, 원시 문서 커밋, raw HWPX XML 작성, 테스트 비활성화.
4. 보완점 — 누락된 테스트, 불완전한 처리, 명백한 개선.

결정:
- APPROVE: 그대로 병합해도 됨 (사소한 취향 문제만 있음).
- FIX: 고칠 수 있는 문제가 있음. fix_instructions에 무엇을 어떻게 고칠지 파일·위치 단위로 구체적으로.
- REJECT: 방향이 틀렸거나 위험해서 버려야 함.

추측 금지: 보고서에 근거가 없는 문제는 issues에 넣지 말 것.
결과는 JSON 스키마에 맞춰서만 출력.

=== TASK ===
{task}

=== AUDIT (자동 정책 검사) ===
{audit}

=== CODEX 마지막 메시지 ===
{last_message}

=== DIFF ({diff_note}) ===
{diff}
"""

FIX_PROMPT = """너는 Codex가 만든 변경을 수정·보완하는 담당이다. 현재 디렉터리는 Codex 작업 브랜치의 worktree다.
원래 요청과 검토 결과를 보고, 지적된 문제만 고쳐라. 범위를 넓히지 말 것. 테스트가 있으면 실행해서 확인.
git commit/push는 하지 말 것 (브리지가 처리).

=== 원래 요청 ===
{task}

=== 검토 결과 ===
{review}
"""


def _claude_cmd(cfg):
    return cfg.get("claude_cmd") or ["claude"]


def _parse_claude_json(stdout):
    """`claude -p --output-format json` -> structured dict (tolerant of shape changes)."""
    try:
        env = json.loads(stdout)
    except ValueError:
        env = {"result": stdout}
    if isinstance(env, dict):
        for key in ("structured_output", "output"):
            if isinstance(env.get(key), dict):
                return env[key], env
        text = env.get("result") or ""
    else:
        text = stdout
    m = re.search(r"\{[\s\S]*\}", text or "")
    if m:
        try:
            return json.loads(m.group(0)), env
        except ValueError:
            pass
    return None, env


def review(cfg, task, audit_report, diff, last_message, coding, timeout=1800):
    model, effort = pick_model(cfg.get("models"), coding)
    max_diff = int(cfg.get("review_max_diff_chars", 120000))
    note = "full" if len(diff) <= max_diff else "truncated to %d of %d chars" % (max_diff, len(diff))
    prompt = REVIEW_PROMPT.format(
        task=task,
        audit=json.dumps({k: audit_report.get(k) for k in ("verdict", "findings", "stats", "commands")},
                         ensure_ascii=False, indent=1),
        last_message=last_message or "(없음)",
        diff_note=note,
        diff=diff[:max_diff] or "(변경 없음)",
    )
    cmd = _claude_cmd(cfg) + [
        "-p", "--model", model, "--effort", effort,
        "--output-format", "json",
        "--json-schema", json.dumps(REVIEW_SCHEMA),
        "--tools", "",
        "--no-session-persistence",
    ]
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    parsed, env = _parse_claude_json(p.stdout)
    if p.returncode != 0 or not parsed or parsed.get("decision") not in ("APPROVE", "FIX", "REJECT"):
        return {"decision": "ERROR", "model": model, "effort": effort, "returncode": p.returncode,
                "stderr": (p.stderr or "")[-2000:], "raw": (p.stdout or "")[-2000:]}
    parsed.update({"model": model, "effort": effort,
                   "cost_usd": env.get("total_cost_usd") if isinstance(env, dict) else None})
    return parsed


def fix_with_claude(cfg, worktree, task, review_result, coding, timeout=3600):
    """Claude edits the Codex worktree directly. Returns run info."""
    model, effort = pick_model(cfg.get("models"), coding)
    prompt = FIX_PROMPT.format(task=task, review=json.dumps(review_result, ensure_ascii=False, indent=1))
    cmd = _claude_cmd(cfg) + [
        "-p", "--model", model, "--effort", effort,
        "--output-format", "json",
        "--permission-mode", "acceptEdits",
        "--allowedTools", cfg.get("fix_allowed_tools",
                                  "Read Edit Write Glob Grep Bash(git diff:*) Bash(git status:*) "
                                  "Bash(python -m pytest:*) Bash(pytest:*) Bash(npm test:*)"),
        "--no-session-persistence",
    ]
    p = subprocess.run(cmd, input=prompt, cwd=worktree, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    _, env = _parse_claude_json(p.stdout)
    return {"fixer": "claude", "model": model, "effort": effort, "returncode": p.returncode,
            "result": ((env.get("result") or "") if isinstance(env, dict) else str(env))[-4000:],
            "stderr": (p.stderr or "")[-2000:]}
