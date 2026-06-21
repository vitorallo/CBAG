#!/usr/bin/env bash
# CBAG — start the stack, wait for health, print the URL. Run ./scripts/build.sh first.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && { set -a; . ./.env; set +a; }
PROFILE=(); [ "${CBAG_BUNDLED_LLM:-0}" = "1" ] && PROFILE=(--profile bundled-llm)
HOST="${CBAG_HOST:-localhost}"; PORT="${CBAG_HTTPS_PORT:-8443}"

echo "Starting CBAG..."
docker compose "${PROFILE[@]}" up -d

echo "Waiting for services to become healthy..."
for _ in $(seq 1 48); do
  sleep 5
  unhealthy=$(docker compose "${PROFILE[@]}" ps --format '{{.Service}} {{.Health}}' \
              | awk '$2!="" && $2!="healthy"{print $1}')
  [ -z "$unhealthy" ] && { echo "All services healthy."; break; }
done

python3 scripts/smoke_test.py --host localhost || true

TS_IP=$(tailscale ip -4 2>/dev/null | head -1 || true)
cat <<EOF

────────────────────────────────────────────────────────
 CBAG is up:
   https://${HOST}:${PORT}
EOF
[ -n "${TS_IP:-}" ] && [ "$TS_IP" != "$HOST" ] && echo "   https://${TS_IP}:${PORT}   (Tailscale)"
cat <<EOF

 First visit shows a self-signed cert warning → Advanced → Proceed.
 (HTTPS is required for the microphone / voice recording.)
 To remove the warning, trust: services/caddy/certs/cbag.crt
────────────────────────────────────────────────────────
EOF
