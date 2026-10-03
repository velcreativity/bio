"""End-to-end test of the bridge with stand-in `codex` and `claude` executables.

    python -m unittest discover -s bridge/tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

BRIDGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BRIDGE)

import audit  # noqa: E402
import jobqueue as jq  # noqa: E402
import local_agent  # noqa: E402
import supervisor  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
os.environ.update(GIT_ENV)

FAKE_CODEX = textwrap.dedent(r'''
    import json, sys, os
    args = sys.argv[1:]
    last = args[args.index("--output-last-message") + 1]
    prompt = sys.stdin.read()
    resumed = "resume" in args
    with open("calc.py", "a") as f:
        f.write("# codex: %s\n" % prompt.strip().splitlines()[0])
    sid = args[args.index("resume") + 1] if resumed else "sess-123"
    for ev in [
        {"type": "thread.started", "thread_id": sid},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "bash -lc 'pytest -q'", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "file_change", "changes": [{"path": "calc.py", "kind": "update"}]}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "done: " + prompt.strip()[:40]}},
        {"type": "turn.completed", "usage": {"input_tokens": 1}},
    ]:
        print(json.dumps(ev))
    open(last, "w").write("done")
''')

FAKE_CLAUDE = textwrap.dedent(r'''
    import json, sys, os
    args = sys.argv[1:]
    stdin = sys.stdin.read()
    log = os.environ["FAKE_CLAUDE_LOG"]
    with open(log, "a") as f:
        f.write(json.dumps({"model": args[args.index("--model") + 1], "effort": args[args.index("--effort") + 1],
                            "mode": "review" if "--json-schema" in args else "fix"}) + "\n")
    if "--json-schema" in args:
        n = sum(1 for _ in open(log))
        decision = "FIX" if n == 1 else "APPROVE"
        out = {"decision": decision, "summary": "s%d" % n, "issues": ["missing test"] if decision == "FIX" else [],
               "fix_instructions": "add a test for add()" if decision == "FIX" else ""}
        print(json.dumps({"type": "result", "result": "", "structured_output": out, "total_cost_usd": 0.01}))
    else:
        with open("test_calc.py", "w") as f:
            f.write("def test_add():\n    assert 1 + 1 == 2\n")
        print(json.dumps({"type": "result", "result": "added test_calc.py"}))
''')


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class AuditTests(unittest.TestCase):
    def test_redact(self):
        text, hits = audit.redact("key=sk-proj-ABCDEFGHIJKLMNOPQRSTUVWX1234 password: hunter22pw 900101-1234567")
        self.assertNotIn("sk-proj-ABC", text)
        self.assertNotIn("hunter22pw", text)
        self.assertNotIn("1234567", text)
        self.assertEqual(hits.get("openai_key"), 1)

    def test_blocks(self):
        ev = json.dumps({"type": "item.completed", "item": {"command": ["bash", "-lc", "git push --force origin main"]}})
        diff = "diff --git a/x.hwpx b/x.hwpx\n+++ b/x.hwpx\n+binary\n"
        rep = audit.audit(ev, diff)
        rules = {f["rule"] for f in rep["findings"]}
        self.assertEqual(rep["verdict"], "BLOCK")
        self.assertIn("CMD-FORCE-PUSH", rules)
        self.assertIn("PATH-RAW-DOC", rules)

    def test_rollout_apply_patch(self):
        rec = {"type": "response_item", "payload": {"type": "function_call", "name": "apply_patch",
               "arguments": json.dumps({"input": "*** Begin Patch\n*** Update File: src/a.py\n@@\n-x\n+y\n*** End Patch"})}}
        act = audit.extract_activity([rec])
        self.assertEqual(act["paths"], ["src/a.py"])

    def test_clean_pass(self):
        rep = audit.audit("", "diff --git a/a.py b/a.py\n+++ b/a.py\n+x = 1\n")
        self.assertEqual(rep["verdict"], "PASS")

    def test_model_routing(self):
        self.assertEqual(supervisor.pick_model({}, supervisor.is_coding(["a.py", "b.ts"])),
                         ("claude-sonnet-5-5", "high"))
        self.assertEqual(supervisor.pick_model({}, supervisor.is_coding(["품질실적.md"])),
                         ("claude-opus-5-5", "high"))
        self.assertTrue(supervisor.is_coding([], "이 함수의 버그를 고쳐줘"))
        self.assertFalse(supervisor.is_coding([], "2026 경영검토서 날짜를 정리해줘"))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        t = self.tmp
        self.remote = os.path.join(t, "remote.git")
        sh(t, "git", "init", "-q", "--bare", "-b", "main", self.remote)
        seed = os.path.join(t, "seed")
        sh(t, "git", "clone", "-q", self.remote, seed)
        for s in jq.STATES:
            os.makedirs(os.path.join(seed, jq.QUEUE_DIR, s))
            open(os.path.join(seed, jq.QUEUE_DIR, s, ".gitkeep"), "w").close()
        sh(seed, "git", "add", "-A")
        sh(seed, "git", "commit", "-q", "-m", "init")
        sh(seed, "git", "push", "-q", "origin", "HEAD:main")
        self.cloud = os.path.join(t, "cloud")
        self.local = os.path.join(t, "local")
        sh(t, "git", "clone", "-q", self.remote, self.cloud)
        sh(t, "git", "clone", "-q", self.remote, self.local)

        self.proj = os.path.join(t, "proj")
        os.makedirs(self.proj)
        sh(self.proj, "git", "init", "-q", "-b", "main")
        with open(os.path.join(self.proj, "calc.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        sh(self.proj, "git", "add", "-A")
        sh(self.proj, "git", "commit", "-q", "-m", "init")

        for name, body in (("fake_codex.py", FAKE_CODEX), ("fake_claude.py", FAKE_CLAUDE)):
            with open(os.path.join(t, name), "w") as f:
                f.write(body)
        self.claude_log = os.path.join(t, "claude.log")
        os.environ["FAKE_CLAUDE_LOG"] = self.claude_log

        self.sessions = os.path.join(t, "codex_sessions", "2026", "10", "03")
        os.makedirs(self.sessions)
        with open(os.path.join(self.sessions, "rollout-x.jsonl"), "w") as f:
            f.write(json.dumps({"type": "session_meta", "payload": {"cwd": "C:/work/app"}}) + "\n")
            f.write(json.dumps({"type": "response_item", "payload": {"type": "function_call", "name": "shell",
                    "arguments": json.dumps({"command": ["bash", "-lc", "echo ghp_" + "a" * 36]})}}) + "\n")

        cfg_path = os.path.join(t, "config.json")
        codex = [sys.executable, os.path.join(t, "fake_codex.py")]
        with open(cfg_path, "w") as f:
            json.dump({
                "repo": self.local, "branch": "main", "workspace": t,
                "projects": {"proj": self.proj},
                "worktree_root": os.path.join(t, "wt"), "state_file": os.path.join(t, "state.json"),
                "codex_exec_cmd": codex + ["--output-last-message", "{last_message_file}", "-"],
                "codex_resume_cmd": codex + ["--output-last-message", "{last_message_file}", "resume", "{session_id}", "-"],
                "claude_cmd": [sys.executable, os.path.join(t, "fake_claude.py")],
                "harvest": {"enabled": True, "sessions_dir": os.path.join(t, "codex_sessions"), "interval_sec": 0},
            }, f)
        self.agent = local_agent.Agent(local_agent.load_config(cfg_path))

    def cloud_submit(self, job):
        jq.write_job(self.cloud, "pending", job)
        jq.git_sync(self.cloud, "main")
        jq.git_commit_push(self.cloud, "main", [os.path.join(jq.QUEUE_DIR, "pending", job["id"] + ".json")], "submit")
        return job["id"]

    def cloud_result(self, job_id):
        jq.git_sync(self.cloud, "main")
        state, job = jq.find_job(self.cloud, job_id)
        self.assertEqual(state, "done", job)
        return job

    def test_codex_review_fix_apply(self):
        jid = self.cloud_submit(jq.make_job("codex.exec", {"project": "proj", "prompt": "add a sub() function"}))
        self.agent.run_once()
        job = self.cloud_result(jid)
        r = job["result"]
        self.assertEqual(job["status"], "ok", r)
        self.assertEqual(r["state"], "approved")
        self.assertEqual(r["fix_rounds"], 1)
        self.assertTrue(r["coding"])
        self.assertEqual((r["model"], r["effort"]), ("claude-sonnet-5-5", "high"))
        self.assertIn("test_calc.py", r["changed_paths"])
        self.assertEqual(r["session_id"], "sess-123")
        with open(self.claude_log) as f:
            calls = [json.loads(l) for l in f]
        self.assertEqual([c["mode"] for c in calls], ["review", "fix", "review"])
        self.assertTrue(all(c["model"] == "claude-sonnet-5-5" and c["effort"] == "high" for c in calls))
        reports = os.listdir(os.path.join(self.cloud, "bridge", "reports", jid))
        for name in ("events.jsonl", "diff.patch", "audit.json", "review_0.json", "fix_1.json", "review_1.json"):
            self.assertIn(name, reports)
        # original project untouched until apply
        with open(os.path.join(self.proj, "calc.py")) as f:
            self.assertNotIn("codex", f.read())

        aid = self.cloud_submit(jq.make_job("codex.apply", {"job_id": jid}))
        self.agent.run_once()
        a = self.cloud_result(aid)
        self.assertEqual(a["status"], "ok", a["result"])
        with open(os.path.join(self.proj, "calc.py")) as f:
            self.assertIn("codex", f.read())
        self.assertTrue(os.path.exists(os.path.join(self.proj, "test_calc.py")))

    def test_harvest_redacts(self):
        self.agent.run_once()
        jq.git_sync(self.cloud, "main")
        idx = os.path.join(self.cloud, "bridge", "codex_logs", "index.jsonl")
        with open(idx) as f:
            rows = [json.loads(l) for l in f]
        self.assertEqual(rows[0]["cwd"], "C:/work/app")
        self.assertEqual(rows[0]["verdict"], "FLAG")  # secret seen in log
        mirrored = [os.path.join(d, f) for d, _, fs in os.walk(os.path.dirname(idx)) for f in fs
                    if f == "rollout-x.jsonl"]
        self.assertEqual(len(mirrored), 1)
        with open(mirrored[0]) as f:
            self.assertNotIn("ghp_aaaa", f.read())

    def test_bad_job_reports_error(self):
        jid = self.cloud_submit(jq.make_job("codex.exec", {"project": "nope", "prompt": "x"}))
        self.agent.run_once()
        job = self.cloud_result(jid)
        self.assertEqual(job["status"], "error")
        self.assertIn("unknown project", job["result"]["error"])


if __name__ == "__main__":
    unittest.main()
