"""Git-backed job queue shared by the cloud Claude session and the local PC agent.

Layout (all paths relative to the repo root):
    bridge/jobs/pending/<id>.json   written by Claude (claude_bridge.py submit)
    bridge/jobs/running/<id>.json   claimed by the local agent
    bridge/jobs/done/<id>.json      job + result, written by the local agent

The repo is the only transport: the local PC makes outbound git pull/push only,
so no inbound port, tunnel or remote-desktop is needed. Raw documents never enter
git (rule R6); results carry metrics, hashes and extracted text instead.
"""
import json
import os
import secrets
import subprocess
import time
from datetime import datetime, timezone

QUEUE_DIR = os.path.join("bridge", "jobs")
STATES = ("pending", "running", "done")

JOB_TYPES = {
    "ping",
    "hancom.page_count",
    "hancom.roundtrip",
    "hancom.convert",
    "hancom.export_pdf",
    "hancom.extract_text",
    "hancom.insert_file",
    "codex.exec",
    "codex.fix",
    "codex.apply",
    "codex.discard",
    "codex.harvest",
    "shell.run",
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job_id():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


def job_path(repo, state, job_id):
    return os.path.join(repo, QUEUE_DIR, state, job_id + ".json")


def list_jobs(repo, state):
    d = os.path.join(repo, QUEUE_DIR, state)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def read_job(repo, state, job_id):
    with open(job_path(repo, state, job_id), encoding="utf-8") as f:
        return json.load(f)


def write_job(repo, state, job):
    path = job_path(repo, state, job["id"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def find_job(repo, job_id):
    for state in STATES:
        if os.path.exists(job_path(repo, state, job_id)):
            return state, read_job(repo, state, job_id)
    return None, None


def make_job(job_type, args, timeout_sec=900, note=""):
    if job_type not in JOB_TYPES:
        raise ValueError("unknown job type %r (allowed: %s)" % (job_type, ", ".join(sorted(JOB_TYPES))))
    return {
        "id": new_job_id(),
        "type": job_type,
        "args": args,
        "timeout_sec": timeout_sec,
        "note": note,
        "created_at": now_iso(),
    }


# ---------------------------------------------------------------- git helpers

class GitError(RuntimeError):
    pass


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise GitError("git %s failed: %s" % (" ".join(args), (p.stderr or p.stdout).strip()))
    return p


def git_sync(repo, branch, retries=4):
    """Fetch + rebase onto origin/<branch>, retrying with backoff on network errors."""
    delay = 2
    for attempt in range(retries + 1):
        p = git(repo, "pull", "--rebase", "origin", branch, check=False)
        if p.returncode == 0:
            return
        if attempt == retries:
            raise GitError("pull failed: " + (p.stderr or p.stdout).strip())
        time.sleep(delay)
        delay *= 2


def git_commit_push(repo, branch, paths, message, retries=4):
    """Stage `paths` (adds and removals), commit, push; rebase and retry on rejection."""
    git(repo, "add", "-A", "--", *paths)
    if git(repo, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git(repo, "commit", "-m", message)
    delay = 2
    for attempt in range(retries + 1):
        p = git(repo, "push", "-u", "origin", branch, check=False)
        if p.returncode == 0:
            return True
        if attempt == retries:
            raise GitError("push failed: " + (p.stderr or p.stdout).strip())
        time.sleep(delay)
        delay *= 2
        git(repo, "pull", "--rebase", "origin", branch, check=False)
    return True
