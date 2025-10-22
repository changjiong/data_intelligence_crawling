#!/usr/bin/env bash
set -euo pipefail
PYV=${1:-3.11}
echo "[uv-setup] Using Python ${PYV}"
if ! command -v uv >/dev/null 2>&1; then
  echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
uv python install ${PYV}
uv venv --python ${PYV} .venv
uv sync
echo "[uv-setup] Done. Try: uv run python src/pipeline.py --dry-run"
