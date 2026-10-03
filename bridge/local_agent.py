"""Local PC agent: executes bridge jobs (Codex, Hancom, shell) and reports back through git.

Run on the Windows PC that has Codex CLI, Claude Code CLI and 한컴오피스:
    python bridge/local_agent.py --config bridge/config.json            # loop forever
    python bridge/local_agent.py --config bridge/config.json --once     # one pass

Every Codex run is supervised:
  1. Codex works in an isolated git worktree on branch codex/<job_id> (never the original);
  2. events + diff are redacted and audited (audit.py);
  3. headless Claude reviews (Opus 5.5 high, or Sonnet 5.5 high for code) and, on FIX,
     corrects/improves the worktree (Claude itself, or Codex resumed with instructions);
  4. the report is pushed; merging into the project happens only on codex.apply
     (or automatically when auto_apply is on and the review approved a clean audit).
"""
import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit  # noqa: E402
import jobqueue as jq  # noqa: E402
import supervisor  # noqa: E402

DEFAULT_CONFIG = {
    "repo": ".",                       # local clone of this bridge repo
    "branch": "main",                  # branch both sides use for jobs
    "workspace": ".",                  # root for hancom/shell relative paths
    "projects": {},                    # name -> local path of a git project Codex may work on
    "worktree_root": "~/.codex_bridge/worktrees",
    "state_file": "~/.codex_bridge/state.json",
    "poll_sec": 30,
    "max_report_bytes": 2000000,
    "codex_exec_cmd": ["codex", "exec", "--json", "--full-auto", "--skip-git-repo-check",
                       "--output-last-message", "{last_message_file}", "-"],
    "codex_resume_cmd": ["codex", "exec", "--json", "--full-auto", "--skip-git-repo-check",
                         "--output-last-message", "{last_message_file}", "resume", "{session_id}", "-"],
    "claude_cmd": ["claude"],
    "models": dict(supervisor.DEFAULT_MODELS),
    "review": {"enabled": True, "max_fix_rounds": 2, "fixer": "codex", "auto_apply": False},
    "harvest": {"enabled": True, "sessions_dir": "~/.codex/sessions", "interval_sec": 600},
    "shell": {"enabled": False, "allow": ["git", "python", "py", "pytest", "npm", "node"]},
}


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    base = os.path.dirname(os.path.abspath(path)) if path else os.getcwd()
    for k in ("repo", "workspace", "worktree_root", "state_file"):
        cfg[k] = os.path.abspath(os.path.join(base, os.path.expanduser(cfg[k])))
    cfg["harvest"]["sessions_dir"] = os.path.expanduser(cfg["harvest"]["sessions_dir"])
    cfg["projects"] = {n: os.path.abspath(os.path.join(base, os.path.expanduser(p)))
                       for n, p in cfg["projects"].items()}
    return cfg


def _which(argv):
    exe = shutil.which(argv[0])
    return [exe] + list(argv[1:]) if exe else list(argv)


def _run(argv, cwd=None, stdin=None, timeout=None):
    return subprocess.run(_which(argv), cwd=cwd, input=stdin, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def _cap(text, limit):
    if len(text) <= limit:
        return text
    head = limit // 4
    return text[:head] + "\n...[TRUNCATED %d chars]...\n" % (len(text) - limit) + text[-(limit - head):]


CODEX_USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def codex_usage(events_text):
    """Sum the token usage of every `turn.completed` event in a Codex --json event stream."""
    out = {"turns": 0}
    out.update((k, 0) for k in CODEX_USAGE_KEYS)
    for rec in audit.parse_jsonl(events_text or ""):
        if not isinstance(rec, dict) or rec.get("type") != "turn.completed":
            continue
        out["turns"] += 1
        usage = rec.get("usage")
        if isinstance(usage, dict):
            for k in CODEX_USAGE_KEYS:
                v = usage.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out[k] += v
    return out


def _add_codex_usage(acc, events_text):
    for k, v in codex_usage(events_text).items():
        acc[k] = acc.get(k, 0) + v


def _new_usage():
    return {"claude": {}, "codex": codex_usage("")}


class Agent:
    def __init__(self, cfg):
        self.cfg = cfg
        self.repo = cfg["repo"]
        self.branch = cfg["branch"]
        self.last_harvest = 0.0

    # ------------------------------------------------------------ plumbing

    def report_dir(self, job_id):
        d = os.path.join(self.repo, "bridge", "reports", job_id)
        os.makedirs(d, exist_ok=True)
        return d

    def write_report(self, job_id, name, content):
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        content, _ = audit.redact(content)
        path = os.path.join(self.report_dir(job_id), name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_cap(content, self.cfg["max_report_bytes"]))
        return os.path.relpath(path, self.repo).replace("\\", "/")

    def ws_path(self, rel):
        root = os.path.realpath(self.cfg["workspace"])
        p = os.path.realpath(os.path.join(root, rel))
        if p != root and not p.startswith(root + os.sep):
            raise ValueError("path escapes workspace: " + rel)
        return p

    def project_path(self, name):
        if name not in self.cfg["projects"]:
            raise ValueError("unknown project %r (configure it under 'projects')" % name)
        return self.cfg["projects"][name]

    def load_state(self):
        try:
            with open(self.cfg["state_file"], encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def save_state(self, state):
        os.makedirs(os.path.dirname(self.cfg["state_file"]), exist_ok=True)
        with open(self.cfg["state_file"], "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)

    def find_done(self, job_id):
        state, job = jq.find_job(self.repo, job_id)
        if state != "done" or not job.get("result"):
            raise ValueError("job %s has no finished result (state=%s)" % (job_id, state))
        return job

    # ------------------------------------------------------------ main loop

    def run_once(self):
        jq.git_sync(self.repo, self.branch)
        for job_id in jq.list_jobs(self.repo, "pending"):
            self.process(job_id)
        h = self.cfg["harvest"]
        if h.get("enabled") and time.time() - self.last_harvest >= h.get("interval_sec", 600):
            self.last_harvest = time.time()
            paths = self.harvest()
            if paths:
                jq.git_commit_push(self.repo, self.branch, paths, "bridge: harvest Codex sessions")

    def process(self, job_id):
        job = jq.read_job(self.repo, "pending", job_id)
        os.remove(jq.job_path(self.repo, "pending", job_id))
        job["claimed_at"] = jq.now_iso()
        job["agent"] = socket.gethostname()
        jq.write_job(self.repo, "running", job)
        claim = [os.path.join(jq.QUEUE_DIR, s, job_id + ".json") for s in ("pending", "running")]
        jq.git_commit_push(self.repo, self.branch, claim, "bridge: claim %s (%s)" % (job_id, job["type"]))

        try:
            result = self.dispatch(job)
            job["status"] = result.pop("_status", "ok")
        except Exception as e:  # report every failure back; never die on one job
            result = {"error": "%s: %s" % (type(e).__name__, e), "traceback": traceback.format_exc()[-4000:]}
            job["status"] = "error"
        job["result"] = result
        job["finished_at"] = jq.now_iso()
        os.remove(jq.job_path(self.repo, "running", job_id))
        jq.write_job(self.repo, "done", job)
        paths = [os.path.join(jq.QUEUE_DIR, s, job_id + ".json") for s in ("running", "done")]
        rd = os.path.join("bridge", "reports", job_id)
        if os.path.isdir(os.path.join(self.repo, rd)):
            paths.append(rd)
        jq.git_commit_push(self.repo, self.branch, paths,
                           "bridge: %s %s -> %s" % (job["type"], job_id, job["status"]))

    def dispatch(self, job):
        t, a = job["type"], job.get("args", {})
        timeout = job.get("timeout_sec", 900)
        if t == "ping":
            return self.do_ping()
        if t.startswith("hancom."):
            return self.do_hancom(job["id"], t.split(".", 1)[1], a)
        if t == "codex.exec":
            return self.do_codex_exec(job["id"], a, timeout)
        if t == "codex.fix":
            return self.do_codex_fix(job["id"], a, timeout)
        if t == "codex.apply":
            return self.do_codex_apply(a)
        if t == "codex.discard":
            return self.do_codex_discard(a)
        if t == "codex.harvest":
            return {"harvested": self.harvest(force=True)}
        if t == "shell.run":
            return self.do_shell(a, timeout)
        raise ValueError("unsupported job type " + t)

    # ------------------------------------------------------------ handlers

    def do_ping(self):
        out = {"host": socket.gethostname(), "platform": platform.platform(), "python": sys.version.split()[0]}
        for name, argv in (("codex", ["codex", "--version"]), ("claude", ["claude", "--version"]),
                           ("git", ["git", "--version"])):
            try:
                out[name] = _run(argv, timeout=60).stdout.strip() or "(no output)"
            except (OSError, subprocess.SubprocessError) as e:
                out[name] = "unavailable: %s" % e
        out["projects"] = sorted(self.cfg["projects"])
        return out

    def do_hancom(self, job_id, op, a):
        import hancom_ops as H
        src = self.ws_path(a["src"])
        dst = self.ws_path(a["dst"]) if a.get("dst") else None
        if op == "page_count":
            return H.page_count(src)
        if op == "roundtrip":
            return H.roundtrip(src, dst)
        if op in ("convert", "export_pdf"):
            return getattr(H, op)(src, dst)
        if op == "extract_text":
            r = H.extract_text(src, a.get("limit", 200000))
            r["text_file"] = self.write_report(job_id, "text.txt", r.pop("text"))
            return r
        if op == "insert_file":
            return H.insert_file(self.ws_path(a["target"]), self.ws_path(a["donor"]), dst,
                                 a.get("keep_section", True))
        raise ValueError("unknown hancom op " + op)

    def do_shell(self, a, timeout):
        sh = self.cfg["shell"]
        argv = a["argv"]
        if not sh.get("enabled"):
            raise PermissionError("shell.run is disabled in config")
        exe = os.path.splitext(os.path.basename(argv[0]))[0].lower()
        if exe not in [x.lower() for x in sh.get("allow", [])]:
            raise PermissionError("executable %r not in shell.allow" % argv[0])
        p = _run(argv, cwd=self.ws_path(a.get("cwd", ".")), timeout=timeout)
        out, _ = audit.redact(p.stdout[-20000:])
        err, _ = audit.redact(p.stderr[-8000:])
        return {"returncode": p.returncode, "stdout": out, "stderr": err,
                "_status": "ok" if p.returncode == 0 else "failed"}

    # ------------------------------------------------------------ codex

    def run_codex(self, prompt, cwd, timeout, session_id=None):
        fd, last_file = tempfile.mkstemp(prefix="codex_last_", suffix=".txt")
        os.close(fd)
        tmpl = self.cfg["codex_resume_cmd"] if session_id else self.cfg["codex_exec_cmd"]
        argv = [x.format(last_message_file=last_file, session_id=session_id or "", cwd=cwd) for x in tmpl]
        try:
            p = _run(argv, cwd=cwd, stdin=prompt, timeout=timeout)
            with open(last_file, encoding="utf-8", errors="replace") as f:
                last = f.read()
        finally:
            os.remove(last_file)
        sid = session_id
        for rec in audit.parse_jsonl(p.stdout):
            for key in ("thread_id", "session_id", "conversation_id"):
                if isinstance(rec, dict) and isinstance(rec.get(key), str):
                    sid = sid or rec[key]
        return {"events": p.stdout, "stderr": p.stderr, "returncode": p.returncode,
                "last_message": last, "session_id": sid}

    def _commit_worktree(self, wt, message):
        jq.git(wt, "add", "-A")
        if jq.git(wt, "diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        jq.git(wt, "-c", "user.name=codex-bridge", "-c", "user.email=codex-bridge@localhost",
               "commit", "-q", "-m", message)
        return True

    def _assess(self, job_id, wt, base, events_text, rnd):
        diff = jq.git(wt, "diff", base, "HEAD").stdout
        rep = audit.audit(events_text, diff)
        self.write_report(job_id, "diff.patch", diff)
        self.write_report(job_id, "audit.json" if rnd == 0 else "audit_%d.json" % rnd, rep)
        return diff, rep

    def _supervise(self, job_id, ctx, timeout, start_round=0):
        """Review -> fix loop on a worktree. Mutates and returns ctx."""
        rv = self.cfg["review"]
        usage = ctx.setdefault("usage", _new_usage())
        coding, ctx["coding_source"] = supervisor.decide_coding(
            self.cfg, ctx["audit"]["changed_paths"], ctx["task"], ctx.get("kind"), usage=usage["claude"])
        ctx["coding"] = coding
        ctx["model"], ctx["effort"] = supervisor.pick_model(self.cfg.get("models"), coding)
        if not rv.get("enabled"):
            ctx["state"] = "needs_review"
            return ctx
        rnd = start_round
        while True:
            rev = supervisor.review(self.cfg, ctx["task"], ctx["audit"], ctx["diff"],
                                    ctx.get("last_message", ""), coding, usage=usage["claude"])
            self.write_report(job_id, "review_%d.json" % rnd, rev)
            ctx["review"] = {k: rev.get(k) for k in ("decision", "summary", "issues", "model", "effort")}
            if rev["decision"] != "FIX" or rnd - start_round >= rv.get("max_fix_rounds", 2):
                break
            rnd += 1
            if rv.get("fixer", "codex") == "claude":
                fx = supervisor.fix_with_claude(self.cfg, ctx["worktree"], ctx["task"], rev, coding, timeout,
                                                usage=usage["claude"])
                extra = ""
            else:
                fx = self.run_codex(rev["fix_instructions"], ctx["worktree"], timeout, ctx.get("session_id"))
                extra = fx.pop("events")
                _add_codex_usage(usage["codex"], extra)
                ctx["events"] += "\n" + extra
                ctx["last_message"] = fx.get("last_message", "")
            self.write_report(job_id, "fix_%d.json" % rnd, fx)
            self._commit_worktree(ctx["worktree"], "bridge: fix round %d (%s)" % (rnd, job_id))
            ctx["diff"], ctx["audit"] = self._assess(job_id, ctx["worktree"], ctx["base"], ctx["events"], rnd)
        ctx["fix_rounds"] = rnd - start_round
        decision = ctx["review"]["decision"]
        if ctx["audit"]["verdict"] == "BLOCK":
            ctx["state"] = "blocked"
        elif decision == "APPROVE":
            ctx["state"] = "approved"
        elif decision == "REJECT":
            ctx["state"] = "rejected"
        else:
            ctx["state"] = "needs_review"
        return ctx

    def _result(self, job_id, ctx):
        out = {k: ctx.get(k) for k in ("project", "branch", "worktree", "base", "session_id", "state",
                                       "coding", "coding_source", "model", "effort", "fix_rounds", "review",
                                       "usage")}
        out["head"] = jq.git(ctx["worktree"], "rev-parse", "HEAD").stdout.strip()
        out["audit_verdict"] = ctx["audit"]["verdict"]
        out["audit_findings"] = ctx["audit"]["findings"][:30]
        out["changed_paths"] = ctx["audit"]["changed_paths"][:200]
        out["report_dir"] = "bridge/reports/" + job_id
        if (ctx["state"] == "approved" and ctx["audit"]["verdict"] == "PASS"
                and self.cfg["review"].get("auto_apply")):
            out["auto_applied"] = self._merge(ctx["project"], ctx["branch"], ctx["worktree"])
            out["state"] = "applied"
        return out

    def do_codex_exec(self, job_id, a, timeout):
        project = a["project"]
        proj = self.project_path(project)
        base = jq.git(proj, "rev-parse", "HEAD").stdout.strip()
        branch = "codex/" + job_id
        wt = os.path.join(self.cfg["worktree_root"], project, job_id)
        os.makedirs(os.path.dirname(wt), exist_ok=True)
        jq.git(proj, "worktree", "add", "-q", "-b", branch, wt, base)

        run = self.run_codex(a["prompt"], wt, timeout, a.get("session_id"))
        self._commit_worktree(wt, "codex: %s" % a["prompt"].splitlines()[0][:72])
        self.write_report(job_id, "events.jsonl", run["events"])
        if run["stderr"].strip():
            self.write_report(job_id, "codex_stderr.txt", run["stderr"][-20000:])
        diff, rep = self._assess(job_id, wt, base, run["events"], 0)
        usage = _new_usage()
        _add_codex_usage(usage["codex"], run["events"])
        ctx = {"project": project, "branch": branch, "worktree": wt, "base": base, "task": a["prompt"],
               "kind": a.get("kind"), "events": run["events"], "last_message": run["last_message"],
               "session_id": run["session_id"], "diff": diff, "audit": rep, "usage": usage}
        self.write_report(job_id, "codex_last_message.md", run["last_message"] or "")
        if run["returncode"] != 0:
            ctx.update(state="codex_failed", review=None, fix_rounds=0)
            r = self._result(job_id, ctx)
            r["codex_returncode"] = run["returncode"]
            r["_status"] = "failed"
            return r
        self._supervise(job_id, ctx, timeout)
        self.write_report(job_id, "context.json", {k: ctx[k] for k in ("task", "kind", "session_id", "base")})
        return self._result(job_id, ctx)

    def do_codex_fix(self, job_id, a, timeout):
        """Cloud Claude's own fix instructions for an earlier codex.exec job."""
        prev = self.find_done(a["job_id"])
        r = prev["result"]
        wt, base = r["worktree"], r["base"]
        if not os.path.isdir(wt):
            raise ValueError("worktree gone (applied or discarded): " + wt)
        task = prev["args"]["prompt"]
        usage = _new_usage()
        coding, coding_source = supervisor.decide_coding(
            self.cfg, r.get("changed_paths", []), task, prev["args"].get("kind"), usage=usage["claude"])
        fixer = a.get("fixer", self.cfg["review"].get("fixer", "codex"))
        review_like = {"decision": "FIX", "summary": "cloud review", "issues": a.get("issues", []),
                       "fix_instructions": a["instructions"]}
        events = ""
        if fixer == "claude":
            fx = supervisor.fix_with_claude(self.cfg, wt, task, review_like, coding, timeout,
                                            usage=usage["claude"])
        else:
            fx = self.run_codex(a["instructions"], wt, timeout, r.get("session_id"))
            events = fx.pop("events")
            _add_codex_usage(usage["codex"], events)
        self.write_report(job_id, "fix.json", fx)
        self._commit_worktree(wt, "bridge: cloud fix %s for %s" % (job_id, a["job_id"]))
        diff, rep = self._assess(job_id, wt, base, events, 0)
        ctx = {"project": r["project"], "branch": r["branch"], "worktree": wt, "base": base, "task": task,
               "kind": prev["args"].get("kind"), "events": events, "last_message": fx.get("last_message", ""),
               "session_id": r.get("session_id"), "diff": diff, "audit": rep, "usage": usage}
        if a.get("rereview", True):
            self._supervise(job_id, ctx, timeout)
        else:
            ctx.update(state="needs_review", review=None, fix_rounds=0, coding=coding, coding_source=coding_source)
            ctx["model"], ctx["effort"] = supervisor.pick_model(self.cfg.get("models"), coding)
        res = self._result(job_id, ctx)
        res["fixes_job"] = a["job_id"]
        return res

    def _merge(self, project, branch, wt):
        proj = self.project_path(project)
        p = jq.git(proj, "merge", "--no-ff", "--no-edit", branch, check=False)
        if p.returncode != 0:
            jq.git(proj, "merge", "--abort", check=False)
            raise RuntimeError("merge failed, aborted: " + (p.stderr or p.stdout).strip())
        jq.git(proj, "worktree", "remove", "--force", wt, check=False)
        jq.git(proj, "branch", "-d", branch, check=False)
        return jq.git(proj, "rev-parse", "HEAD").stdout.strip()

    def _latest_for(self, job_id):
        """The newest done job about this codex.exec (itself or a later codex.fix)."""
        latest = self.find_done(job_id)
        for jid in jq.list_jobs(self.repo, "done"):
            j = jq.read_job(self.repo, "done", jid)
            if j["type"] == "codex.fix" and j.get("args", {}).get("job_id") == job_id and j.get("result") \
                    and jid > latest["id"]:
                latest = j
        return latest

    def do_codex_apply(self, a):
        latest = self._latest_for(a["job_id"])
        r = latest["result"]
        if r.get("audit_verdict") == "BLOCK" and not a.get("override_reason"):
            raise PermissionError("audit verdict BLOCK; pass override_reason to apply anyway")
        head = self._merge(r["project"], r["branch"], r["worktree"])
        return {"applied": a["job_id"], "from_job": latest["id"], "project": r["project"], "head": head,
                "override_reason": a.get("override_reason")}

    def do_codex_discard(self, a):
        r = self.find_done(a["job_id"])["result"]
        proj = self.project_path(r["project"])
        jq.git(proj, "worktree", "remove", "--force", r["worktree"], check=False)
        jq.git(proj, "branch", "-D", r["branch"], check=False)
        return {"discarded": a["job_id"], "branch": r["branch"], "reason": a.get("reason", "")}

    # ------------------------------------------------------------ harvest

    def harvest(self, force=False):
        """Mirror every Codex session (interactive ones too) into git, redacted and audited."""
        root = self.cfg["harvest"]["sessions_dir"]
        if not os.path.isdir(root):
            return []
        state = self.load_state()
        seen = state.setdefault("harvested", {})
        out_dir = os.path.join(self.repo, "bridge", "codex_logs")
        index_lines, written = [], []
        for dirpath, _, files in os.walk(root):
            for name in sorted(files):
                if not name.endswith(".jsonl"):
                    continue
                src = os.path.join(dirpath, name)
                size = os.path.getsize(src)
                if not force and seen.get(src) == size:
                    continue
                with open(src, encoding="utf-8", errors="replace") as f:
                    text = f.read()
                recs = audit.parse_jsonl(text)
                cwd = next((r.get("payload", {}).get("cwd") for r in recs
                            if isinstance(r, dict) and isinstance(r.get("payload"), dict)
                            and r["payload"].get("cwd")), None)
                rep = audit.audit(text)
                day = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(src)))
                rel_dir = os.path.join(out_dir, day)
                os.makedirs(rel_dir, exist_ok=True)
                red, _ = audit.redact(text)
                with open(os.path.join(rel_dir, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(_cap(red, self.cfg["max_report_bytes"]))
                with open(os.path.join(rel_dir, name[:-6] + ".audit.json"), "w", encoding="utf-8",
                          newline="\n") as f:
                    json.dump({"source": name, "cwd": cwd, **rep}, f, ensure_ascii=False, indent=1)
                index_lines.append(json.dumps({
                    "harvested_at": jq.now_iso(), "file": "%s/%s" % (day, name), "cwd": cwd,
                    "verdict": rep["verdict"], "findings": len(rep["findings"]),
                    "commands": rep["stats"]["commands"], "changed_paths": rep["stats"]["changed_paths"],
                    "last_message": rep["last_message"][:300],
                }, ensure_ascii=False))
                seen[src] = size
                written.append(os.path.relpath(rel_dir, self.repo))
        if index_lines:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "index.jsonl"), "a", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(index_lines) + "\n")
            written.append(os.path.relpath(os.path.join(out_dir, "index.jsonl"), self.repo))
        self.save_state(state)
        return sorted(set(written))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.config)
    agent = Agent(cfg)
    print("bridge agent: repo=%s branch=%s projects=%s" % (cfg["repo"], cfg["branch"], ", ".join(cfg["projects"])))
    while True:
        try:
            agent.run_once()
        except Exception:  # network blips etc.: log and keep polling
            traceback.print_exc()
        if a.once:
            break
        time.sleep(cfg["poll_sec"])


if __name__ == "__main__":
    main()
