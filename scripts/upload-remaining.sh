#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Push entire local main history once authenticated
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin https://github.com/DZeiler03/verto.git
fi
# Prefer force-with-lease only if histories diverge; otherwise normal push
git fetch origin main 2>/dev/null || true
if git rev-parse origin/main >/dev/null 2>&1; then
  # Rebase local on remote then push, or force if needed for clean history
  echo "Remote exists. To replace remote with full local tree:"
  echo "  git push -u origin main --force"
  echo "Or merge carefully. Prefer:"
  echo "  /tmp/gh_2.74.1_linux_amd64/bin/gh auth login"
  echo "  git push -u origin main --force"
else
  git push -u origin main
fi
