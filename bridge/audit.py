"""Policy engine: redact secrets and audit Codex activity (event streams, rollouts, diffs).

Used on both sides of the bridge:
  - local agent: redacts before anything is pushed, attaches a first-pass verdict;
  - Claude (cloud): re-runs the audit on the pushed report before approve/reject.

Verdicts: PASS (nothing found) < FLAG (needs Claude's eyes) < BLOCK (never apply
without an explicit override). The parser is tolerant of Codex format changes: it
walks any JSON and collects shell commands, file paths and agent messages wherever
they appear (`codex exec --json` items, ~/.codex/sessions rollout function_calls).
"""
import json
import re
import sys

SEVERITY = {"PASS": 0, "FLAG": 1, "BLOCK": 2}

# ------------------------------------------------------------------ redaction

SECRET_PATTERNS = [
    ("openai_key", re.compile(r"sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
    ("assignment", re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b(\s*[:=]\s*)(['\"]?)[^\s'\"]{6,}\3")),
    ("kr_rrn", re.compile(r"\b\d{6}-[1-4]\d{6}\b")),  # 주민등록번호
]


def redact(text):
    """Return (redacted_text, {pattern_name: count})."""
    hits = {}

    def sub(name):
        def _r(m):
            hits[name] = hits.get(name, 0) + 1
            if name == "assignment":
                return m.group(1) + m.group(2) + "[REDACTED]"
            return "[REDACTED:%s]" % name
        return _r

    for name, pat in SECRET_PATTERNS:
        text = pat.sub(sub(name), text)
    return text, hits


# --------------------------------------------------------------------- rules

# (rule_id, verdict, regex over a single shell command string, description)
COMMAND_RULES = [
    ("CMD-RM-ROOT", "BLOCK", r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+(/|~|\$HOME|[A-Za-z]:\\)(\s|$)", "recursive delete of root/home"),
    ("CMD-RMDIR-S", "BLOCK", r"(?i)\b(rmdir|rd)\s+/s\b.*[A-Za-z]:\\\s*$", "recursive delete of a drive"),
    ("CMD-FORMAT", "BLOCK", r"(?i)\b(format\s+[A-Za-z]:|mkfs\.|diskpart)", "disk format"),
    ("CMD-PIPE-SHELL", "BLOCK", r"(curl|wget|iwr|Invoke-WebRequest)[^|]*\|\s*(sh|bash|iex|Invoke-Expression|python)", "download piped to a shell"),
    ("CMD-FORCE-PUSH", "BLOCK", r"\bgit\s+push\b.*(--force\b|-f\b|--force-with-lease)", "force push"),
    ("CMD-HISTORY-REWRITE", "FLAG", r"\bgit\s+(reset\s+--hard|rebase|filter-branch|filter-repo|commit\s+--amend)", "history rewrite"),
    ("CMD-GIT-PUSH", "FLAG", r"\bgit\s+push\b", "Codex pushed by itself (pushes belong to the bridge)"),
    ("CMD-REG", "BLOCK", r"(?i)\breg\s+(add|delete)\b|Set-ItemProperty\s+.*HK(LM|CU)", "registry modification"),
    ("CMD-EXEC-POLICY", "BLOCK", r"(?i)Set-ExecutionPolicy|-ExecutionPolicy\s+Bypass", "execution policy bypass"),
    ("CMD-DEFENDER", "BLOCK", r"(?i)Set-MpPreference|Add-MpPreference", "antivirus tampering"),
    ("CMD-CRED-READ", "BLOCK", r"(?i)(\.ssh[\\/]id_|\.aws[\\/]credentials|\.codex[\\/]auth\.json|\.git-credentials|cmdkey\s+/list|Login Data)", "credential store access"),
    ("CMD-ENV-DUMP", "FLAG", r"(?i)^\s*(env|printenv|set|Get-ChildItem\s+env:|gci\s+env:)\s*$", "environment dump"),
    ("CMD-SUDO", "FLAG", r"(?i)\b(sudo|runas)\b", "privilege escalation"),
    ("CMD-INSTALL", "FLAG", r"(?i)\b(pip|pip3|npm|pnpm|yarn|choco|winget|apt|apt-get)\s+(install|add|i)\b", "package install"),
    ("CMD-NETWORK", "FLAG", r"(?i)\b(curl|wget|Invoke-WebRequest|iwr|scp|ftp|nc|ncat)\b", "network access"),
    ("CMD-SCHEDULE", "BLOCK", r"(?i)\b(schtasks\s+/create|crontab\s+-|New-ScheduledTask)", "persistence via scheduler"),
]

# (rule_id, verdict, regex over a changed path, description)
PATH_RULES = [
    ("PATH-RAW-DOC", "BLOCK", r"(?i)\.(hwp|hwpx|pdf|docx?|xlsx?|zip)$", "raw document committed (R6)"),
    ("PATH-SECRET-FILE", "BLOCK", r"(?i)(^|/)(\.env(\..*)?|id_rsa|id_ed25519|.*\.pem|.*\.key|credentials(\.json)?|auth\.json)$", "secret file"),
    ("PATH-CI", "FLAG", r"(^|/)\.github/workflows/", "CI workflow change"),
    ("PATH-GIT-INTERNALS", "BLOCK", r"(^|/)\.git/", "edit inside .git"),
    ("PATH-HOOKS", "FLAG", r"(^|/)(\.claude|\.codex|\.husky)/", "agent/hook config change"),
    ("PATH-BRIDGE", "FLAG", r"^bridge/", "Codex edited the supervision bridge itself"),
    ("PATH-GITIGNORE", "FLAG", r"(^|/)\.gitignore$", ".gitignore change (can un-ignore raw documents)"),
]

# (rule_id, verdict, regex over added diff lines, description)
DIFF_RULES = [
    ("DIFF-SECRET", "BLOCK", None, "secret in added lines"),  # handled via redact()
    ("DIFF-RAW-XML-HWPX", "FLAG", r"<hp:(p|run|tbl|tc)\b", "raw HWPX XML authoring (forbidden: dangling style refs)"),
    ("DIFF-DISABLED-TEST", "FLAG", r"(@pytest\.mark\.skip|\bit\.skip\(|\bxit\(|unittest\.skip)", "test disabled"),
    ("DIFF-EVAL", "FLAG", r"\b(eval|exec)\s*\(|subprocess\.[a-z_]+\(.*shell\s*=\s*True", "dynamic code execution"),
    ("DIFF-TLS-OFF", "BLOCK", r"verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|--insecure\b", "TLS verification disabled"),
]


def _compile(rules):
    return [(rid, v, re.compile(rx) if rx else None, d) for rid, v, rx, d in rules]


_CMD = _compile(COMMAND_RULES)
_PATH = _compile(PATH_RULES)
_DIFF = _compile(DIFF_RULES)


# ------------------------------------------------------------------ extract

def _cmd_to_str(c):
    if isinstance(c, list):
        # ["bash","-lc","..."] / ["powershell","-Command","..."] -> inner script
        if len(c) >= 3 and str(c[-2]).lower() in ("-lc", "-c", "-command", "/c"):
            return str(c[-1])
        return " ".join(str(x) for x in c)
    return str(c)


PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.M)


def extract_activity(records):
    """Walk parsed JSON records; return {'commands': [...], 'paths': [...], 'messages': [...]}."""
    out = {"commands": [], "paths": [], "messages": []}

    def walk(o, parent_key=None):
        if isinstance(o, dict):
            t = o.get("type")
            for k, v in o.items():
                if k in ("command", "cmd") and isinstance(v, (str, list)):
                    out["commands"].append(_cmd_to_str(v))
                elif k == "arguments" and isinstance(v, str):
                    try:
                        walk(json.loads(v), k)
                    except ValueError:
                        pass
                elif k == "path" and isinstance(v, str) and parent_key in ("changes", "changes_item"):
                    out["paths"].append(v)
                elif k in ("input", "patch") and isinstance(v, str) and "*** Begin Patch" in v:
                    out["paths"].extend(PATCH_FILE.findall(v))
                elif k == "text" and t in ("agent_message", "output_text") and isinstance(v, str):
                    out["messages"].append(v)
                elif k == "changes" and isinstance(v, dict):  # apply_patch style {path: {...}}
                    out["paths"].extend(v.keys())
                    walk(v, k)
                else:
                    walk(v, k + "_item" if isinstance(v, list) else k)
        elif isinstance(o, list):
            for x in o:
                walk(x, parent_key)

    for r in records:
        walk(r)
    for key in out:
        seen, uniq = set(), []
        for x in out[key]:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        out[key] = uniq
    return out


def parse_jsonl(text):
    recs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except ValueError:
            pass
    return recs


def diff_changed_paths(diff_text):
    return re.findall(r"^diff --git a/(.+?) b/", diff_text, flags=re.M)


def diff_added_lines(diff_text):
    return [l[1:] for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]


# -------------------------------------------------------------------- audit

def audit(events_text="", diff_text="", extra_paths=()):
    """Return a report dict: verdict, findings[], stats."""
    findings = []

    def add(rid, verdict, desc, evidence):
        findings.append({"rule": rid, "verdict": verdict, "desc": desc, "evidence": evidence[:300]})

    act = extract_activity(parse_jsonl(events_text)) if events_text else {"commands": [], "paths": [], "messages": []}
    for cmd in act["commands"]:
        for rid, v, rx, d in _CMD:
            if rx.search(cmd):
                add(rid, v, d, cmd)

    paths = list(dict.fromkeys(list(act["paths"]) + diff_changed_paths(diff_text) + list(extra_paths)))
    for p in paths:
        norm = p.replace("\\", "/")
        for rid, v, rx, d in _PATH:
            if rx.search(norm):
                add(rid, v, d, p)

    added = diff_added_lines(diff_text)
    _, secret_hits = redact("\n".join(added))
    if secret_hits:
        add("DIFF-SECRET", "BLOCK", "secret in added lines", json.dumps(secret_hits))
    for line in added:
        for rid, v, rx, d in _DIFF:
            if rx is not None and rx.search(line):
                add(rid, v, d, line.strip())

    _, event_secrets = redact(events_text)
    if event_secrets:
        add("LOG-SECRET", "FLAG", "secret appeared in Codex log (redacted before push)", json.dumps(event_secrets))

    verdict = "PASS"
    for f in findings:
        if SEVERITY[f["verdict"]] > SEVERITY[verdict]:
            verdict = f["verdict"]
    return {
        "verdict": verdict,
        "findings": findings,
        "stats": {
            "commands": len(act["commands"]),
            "changed_paths": len(paths),
            "added_lines": len(added),
            "messages": len(act["messages"]),
        },
        "commands": act["commands"][:200],
        "changed_paths": paths[:500],
        "last_message": act["messages"][-1][:4000] if act["messages"] else "",
    }


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Audit Codex events/diff")
    ap.add_argument("--events", help="events.jsonl or rollout-*.jsonl")
    ap.add_argument("--diff", help="unified diff file")
    a = ap.parse_args(argv)
    ev = open(a.events, encoding="utf-8", errors="replace").read() if a.events else ""
    df = open(a.diff, encoding="utf-8", errors="replace").read() if a.diff else ""
    rep = audit(ev, df)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return SEVERITY[rep["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
