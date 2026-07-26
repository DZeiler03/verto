#!/usr/bin/env bash
# Build a standalone Linux binary for Verto with PyInstaller.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt
pip install -q pyinstaller

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

pyinstaller --noconfirm packaging/verto.spec

echo ""
echo "Built: ${ROOT}/dist/verto"
echo "Run with: ./dist/verto"
echo ""
echo "Optional: install desktop entry"
echo "  cp packaging/verto.desktop ~/.local/share/applications/"
echo "  # copy binary to ~/bin or /usr/local/bin as 'verto'"
