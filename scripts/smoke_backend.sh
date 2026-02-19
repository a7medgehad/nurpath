#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "[smoke] checking root"
curl -fsS "$BASE_URL/" >/dev/null

echo "[smoke] creating session"
SESSION_ID=$(curl -fsS -X POST "$BASE_URL/v1/sessions" \
  -H 'Content-Type: application/json' \
  -d '{"preferred_language":"en","level":"beginner","goals":["smoke"]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])')

echo "[smoke] asking question"
curl -fsS -X POST "$BASE_URL/v1/ask" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"$SESSION_ID\",\"question\":\"What is wudu?\",\"preferred_language\":\"en\"}" >/dev/null

echo "[smoke] retrieval health"
curl -fsS "$BASE_URL/v1/health/retrieval" >/dev/null

echo "[smoke] passed"
