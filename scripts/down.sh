#!/usr/bin/env bash
# CBAG — stop the stack. Keeps model volumes by default (fast restart).
#   ./scripts/down.sh            # stop, keep weights
#   ./scripts/down.sh --purge    # stop AND delete volumes (weights must be re-fetched)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--purge" ]; then
  echo "Stopping CBAG and REMOVING all volumes (model weights will need re-downloading)…"
  docker compose --profile bundled-llm down -v
else
  echo "Stopping CBAG (model volumes kept; use --purge to remove them)…"
  docker compose --profile bundled-llm down
fi
