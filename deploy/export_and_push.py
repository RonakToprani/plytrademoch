#!/usr/bin/env python
"""
Export the paper state snapshot and push it to main so the scheduled cloud Opus
routine can read it. Invoked by launchd via the venv python (a plain shell
script in ~/Documents is blocked by macOS TCC under launchd). Uses a dedicated
worktree so the main repo checkout / WIP is never touched.
"""

import datetime
import os
import shutil
import subprocess
import sys

REPO = "/Users/ronaktoprani/Documents/plytrademoch"
WT = "/private/tmp/poly-main-wt"


def git(*args, cwd=REPO, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check,
                          capture_output=True, text=True)


def main() -> int:
    os.chdir(REPO)
    sys.path.insert(0, REPO)
    git("fetch", "origin", "--quiet")

    if os.path.exists(os.path.join(WT, ".git")):
        git("reset", "--hard", "origin/main", "--quiet", cwd=WT)
    else:
        shutil.rmtree(WT, ignore_errors=True)
        git("worktree", "add", "-B", "main", WT, "origin/main", "--quiet")

    from paper.export import write_state
    write_state(os.path.join(WT, "reports", "state.md"))

    git("add", "reports/state.md", cwd=WT)
    if git("diff", "--cached", "--quiet", cwd=WT, check=False).returncode == 0:
        print("no state change")
        return 0
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    git("commit", "--quiet", "-m", f"chore: paper state snapshot {ts}", cwd=WT)
    git("push", "--quiet", "origin", "main", cwd=WT)
    print("pushed state snapshot")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"git failed: {exc.cmd}\n{exc.stderr}", file=sys.stderr)
        sys.exit(1)
