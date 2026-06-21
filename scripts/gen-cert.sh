#!/usr/bin/env bash
# Generate the self-signed multi-SAN cert Caddy serves (services/caddy/certs/).
# Browsers send no SNI for bare IPs, so we serve ONE cert covering every address
# the app is reached on. Pass extra SANs via CBAG_SANS to add IPs/hostnames.
#
#   ./scripts/gen-cert.sh
#   CBAG_SANS="DNS:localhost,IP:127.0.0.1,IP:192.168.1.42,IP:100.64.0.1,DNS:my-spark.example.ts.net" ./scripts/gen-cert.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/services/caddy/certs"
mkdir -p "$DIR"

# Default covers loopback only; build.sh auto-detects this box's LAN/Tailscale IPs
# and passes them via CBAG_SANS so the cert matches however you reach the box.
SANS="${CBAG_SANS:-DNS:localhost,IP:127.0.0.1}"

openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
	-keyout "$DIR/cbag.key" -out "$DIR/cbag.crt" \
	-subj "/CN=CBAG local" \
	-addext "subjectAltName=${SANS}" \
	-addext "basicConstraints=CA:FALSE" >/dev/null 2>&1

chmod 600 "$DIR/cbag.key"
echo "wrote $DIR/cbag.{crt,key}"
echo "SANs: ${SANS}"
