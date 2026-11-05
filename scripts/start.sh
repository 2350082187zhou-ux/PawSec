#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  bash scripts/setup.sh
fi
exec .venv/bin/python tools/local.py start
