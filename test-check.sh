#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

printf '%s\n' '==> Python syntax check'
python -m compileall -q app tests

printf '%s\n' '==> Unit tests'
python -m pytest -m unit -q

printf '%s\n' '==> Integration tests'
python -m pytest -m integration -q

printf '%s\n' '==> All checks passed'
