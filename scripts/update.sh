#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v git >/dev/null || { echo 'Install git first.'; exit 1; }
exec python3 tools/update_local.py
