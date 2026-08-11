#!/usr/bin/env bash
# Upload remaining Verto sources if git push fails
# Requires: gh auth login
set -euo pipefail
cd "$(dirname "$0")/.."
git remote add origin https://github.com/DZeiler03/verto.git 2>/dev/null || true
git push -u origin main
