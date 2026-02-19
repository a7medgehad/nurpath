#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="/tmp/nurpath_backend_e2e.log"
FRONTEND_LOG="/tmp/nurpath_frontend_e2e.log"
E2E_DB="$ROOT_DIR/backend/e2e_nurpath.db"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$E2E_DB"
}
trap cleanup EXIT

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    kill $pids >/dev/null 2>&1 || true
  fi
}

cd "$ROOT_DIR"
free_port 8000
free_port 3000

source backend/.venv/bin/activate
DATABASE_URL="sqlite:///$E2E_DB" QDRANT_LOCAL_MODE=true \
  uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000 >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1 && curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

npm run e2e
