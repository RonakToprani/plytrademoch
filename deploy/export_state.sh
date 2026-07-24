#!/bin/bash
# Export the paper state snapshot and push it to main, so the scheduled cloud
# Opus routine (which can't see the local DB) can read it. Uses a dedicated
# worktree so the main repo checkout / WIP is never touched.
set -euo pipefail
REPO="/Users/ronaktoprani/Documents/plytrademoch"
WT="/private/tmp/poly-main-wt"
cd "$REPO"

git fetch origin --quiet
if [ -d "$WT/.git" ] || git -C "$WT" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$WT" reset --hard origin/main --quiet
else
  rm -rf "$WT"
  git worktree add -B main "$WT" origin/main --quiet
fi

"$REPO/venv/bin/python" -m paper.run export --out "$WT/reports/state.md" >/dev/null

cd "$WT"
git add reports/state.md
if git diff --cached --quiet; then
  echo "no state change"
  exit 0
fi
git commit --quiet -m "chore: paper state snapshot $(date -u +%Y-%m-%dT%H:%MZ)"
git push --quiet origin main
echo "pushed state snapshot"
