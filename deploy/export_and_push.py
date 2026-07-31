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
# NOT under /private/tmp — macOS purges files there after ~3 days, which deletes
# the worktree while git still has `main` registered to the path, and every later
# run then dies on "fatal: 'main' is already checked out at ...".
WT = os.path.expanduser("~/Library/Caches/poly-main-wt")


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
        # Drop any registration pointing at a worktree dir that no longer exists,
        # otherwise `worktree add` fails with "already checked out".
        git("worktree", "prune")
        # --detach, NOT `-B main`: a worktree that holds the main branch makes it
        # impossible to check main out in the primary repo ("fatal: 'main' is
        # already checked out at ..."). Detached HEAD tracks the same commit
        # without claiming the branch name.
        git("worktree", "add", "--detach", WT, "origin/main", "--quiet")

    from paper.export import write_state
    write_state(os.path.join(WT, "reports", "state.md"))

    git("add", "reports/state.md", cwd=WT)
    if git("diff", "--cached", "--quiet", cwd=WT, check=False).returncode == 0:
        print("no state change")
        return 0
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    git("commit", "--quiet", "-m", f"chore: paper state snapshot {ts}", cwd=WT)
    git("push", "--quiet", "origin", "HEAD:main", cwd=WT)
    print("pushed state snapshot")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"git failed: {exc.cmd}\n{exc.stderr}", file=sys.stderr)
        sys.exit(1)
