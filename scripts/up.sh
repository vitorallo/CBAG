#!/usr/bin/env bash
# Build and bring up the CBAG stack.
#   ./scripts/up.sh                 # reuse an existing host Ollama (default)
#   ./scripts/up.sh --bundled-llm   # also start a bundled Ollama container
#                                   # (set LLM_BASE_URL=http://llm:11434 in .env)
set -euo pipefail
cd "$(dirname "$0")/.."

PROFILE_ARGS=()
if [[ "${1:-}" == "--bundled-llm" ]]; then
  PROFILE_ARGS=(--profile bundled-llm)
  echo "Starting with bundled Ollama (profile: bundled-llm)."
fi

docker compose "${PROFILE_ARGS[@]}" up -d --build --remove-orphans

echo
echo "Containers:"
docker compose ps
echo
echo "Waiting for health (Ctrl-C to stop watching)..."
for i in $(seq 1 30); do
  sleep 5
  if docker compose ps --format '{{.Service}} {{.Health}}' | grep -qv 'healthy'; then
    docker compose ps --format '{{.Service}}: {{.Health}}'
  else
    echo "All services healthy."
    break
  fi
done
