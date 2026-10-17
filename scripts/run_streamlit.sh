#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export BACKEND_URL="${BACKEND_URL:-http://localhost:${BACKEND_PORT:-8010}}"
exec uv run streamlit run app/streamlit_app.py --server.port "${STREAMLIT_PORT:-8501}"
