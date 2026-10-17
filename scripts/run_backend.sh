#!/usr/bin/env bash
# Start Neo4j (if needed), seed demo data and run the FastAPI backend.
# GRAPH_BACKEND=memory skips Neo4j entirely.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${GRAPH_BACKEND:-neo4j}" == "neo4j" ]]; then
  docker compose -f docker/docker-compose.yml up -d --wait
  uv run python scripts/seed_neo4j.py
fi
exec uv run uvicorn backend.main:app --host 127.0.0.1 --port "${BACKEND_PORT:-8010}"
