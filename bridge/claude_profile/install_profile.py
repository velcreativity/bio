"""Deploy the model policy (Opus 5.5 high for general work, Sonnet 5.5 high for code) everywhere.

    python install_profile.py --user                 # ~/.claude  -> every project on this PC
    python install_profile.py --project C:/work/app  # one project (<project>/.claude + CLAUDE.md)
    python install_profile.py --scan C:/work         # every git repo directly under C:/work
    add --dry-run to see what would change

Idempotent: settings.json is merged (other keys kept), the CLAUDE.md block between the
BEGIN/END markers is replaced in place, agents are overwritten with the current version.
"""
import argparse
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
BEGIN = "<!-- codex-bridge model policy: BEGIN"
END = "<!-- codex-bridge model policy: END -->"


def merge_settings(path, dry):
    with open(os.path.join(HERE, "settings.json"), encoding="utf-8") as f:
        ours = json.load(f)
    cur = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cur = json.load(f)
    new = dict(cur, **ours)
    if new == cur:
        return "unchanged " + path
    if not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return "merged    " + path


def upsert_block(path, dry):
    with open(os.path.join(HERE, "CLAUDE.md"), encoding="utf-8") as f:
        block = f.read().strip() + "\n"
    cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)
    if pat.search(cur):
        new = pat.sub(lambda _: block, cur)
    else:
        new = (cur.rstrip() + "\n\n" if cur.strip() else "") + block
    if new == cur:
        return "unchanged " + path
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return "updated   " + path


def copy_agents(dst_dir, dry):
    out = []
    src_dir = os.path.join(HERE, "agents")
    for name in sorted(os.listdir(src_dir)):
        dst = os.path.join(dst_dir, name)
        src = os.path.join(src_dir, name)
        if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
            out.append("unchanged " + dst)
            continue
        if not dry:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src, dst)
        out.append("copied    " + dst)
    return out


def install(claude_dir, claude_md, dry):
    log = [merge_settings(os.path.join(claude_dir, "settings.json"), dry),
           upsert_block(claude_md, dry)]
    log += copy_agents(os.path.join(claude_dir, "agents"), dry)
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--user", action="store_true")
    g.add_argument("--project")
    g.add_argument("--scan")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    targets = []
    if a.user:
        home = os.path.join(os.path.expanduser("~"), ".claude")
        targets.append((home, os.path.join(home, "CLAUDE.md")))
    else:
        roots = [a.project] if a.project else [
            os.path.join(a.scan, d) for d in sorted(os.listdir(a.scan))
            if os.path.isdir(os.path.join(a.scan, d, ".git"))]
        for r in roots:
            r = os.path.abspath(r)
            targets.append((os.path.join(r, ".claude"), os.path.join(r, "CLAUDE.md")))
    for claude_dir, md in targets:
        for line in install(claude_dir, md, a.dry_run):
            print(("[dry] " if a.dry_run else "") + line)


if __name__ == "__main__":
    main()
