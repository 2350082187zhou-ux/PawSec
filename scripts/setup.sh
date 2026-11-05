#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo 'Install Python 3.12+: sudo apt install python3 python3-venv'; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else "Python 3.12+ is required")'
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || { echo 'On Ubuntu: sudo apt install python3-venv'; exit 1; }
fi
.venv/bin/python -m pip install -r requirements.txt
if [[ "${1:-}" == '--pptx' ]]; then
  command -v node >/dev/null && command -v npm >/dev/null || { echo 'Optional PPTX export requires Node.js 20+ and npm.'; exit 1; }
  node -e 'if (+process.versions.node.split(".")[0] < 20) process.exit(1)'
  npm ci --omit=dev --ignore-scripts
fi
.venv/bin/python tools/local.py doctor
