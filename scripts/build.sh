#!/usr/bin/env bash
# CBAG — one-command build for a DGX Spark (GB10, aarch64, CUDA 13).
# Preflight -> autoconfigure (.env + cert for THIS box) -> build images -> fetch models.
# Everything builds on the box from source; no prebaked images, no bundled weights.
# Idempotent: safe to re-run. Then: ./scripts/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✗ %s\033[0m\n' "$*"; exit 1; }
step() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

set_env() { # set_env KEY VALUE  (update-or-append in .env)
  local k="$1" v="$2"
  if grep -q "^${k}=" .env 2>/dev/null; then sed -i "s|^${k}=.*|${k}=${v}|" .env
  else echo "${k}=${v}" >> .env; fi
}

# --- 1. Preflight ---------------------------------------------------------------
step "Preflight"
[ "$(uname -m)" = "aarch64" ] && ok "arch aarch64" || warn "arch $(uname -m) (this targets the GB10/aarch64)"
command -v docker >/dev/null || die "docker not found"
docker compose version >/dev/null 2>&1 || die "docker compose v2 not found"
ok "docker + compose v2"
if docker info 2>/dev/null | grep -qi nvidia || nvidia-smi >/dev/null 2>&1; then ok "NVIDIA GPU/runtime"
else warn "NVIDIA Container Toolkit not detected — GPU passthrough may fail"; fi
FREE_GB=$(($(df -Pk . | awk 'NR==2{print $4}') / 1024 / 1024))
[ "$FREE_GB" -ge 50 ] && ok "disk free ${FREE_GB}GB" || warn "only ${FREE_GB}GB free (need ~50GB for images + weights)"
ss -ltnH 2>/dev/null | grep -q ':443 ' && warn "port 443 is taken (Dell demo?) — CBAG uses 8443"
for p in 80 "${CBAG_HTTPS_PORT:-8443}"; do
  ss -ltnH 2>/dev/null | grep -q ":${p} " && warn "port ${p} already in use" || ok "port ${p} free"
done

# --- 2. Autoconfigure .env (detect this box) ------------------------------------
step "Configure"
[ -f .env ] || { cp .env.example .env; ok "created .env from .env.example"; }
LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++)if($i=="src"){print $(i+1);exit}}')
TS_IP=$(tailscale ip -4 2>/dev/null | head -1 || true)
SANS="DNS:localhost,IP:127.0.0.1"
[ -n "${LAN_IP:-}" ] && SANS="${SANS},IP:${LAN_IP}"
[ -n "${TS_IP:-}" ]  && SANS="${SANS},IP:${TS_IP}"
HOST="${LAN_IP:-${TS_IP:-localhost}}"
set_env CBAG_HOST "$HOST"
set_env CBAG_SANS "$SANS"
ok "host=${HOST}  SANs=${SANS}"

# LLM: reuse a host Ollama if one is reachable, else use the bundled one.
if curl -fsS -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  set_env LLM_BASE_URL "http://host.docker.internal:11434"; set_env CBAG_BUNDLED_LLM "0"
  ok "using existing host Ollama (:11434)"
else
  set_env LLM_BASE_URL "http://llm:11434"; set_env CBAG_BUNDLED_LLM "1"
  ok "no host Ollama — will use the bundled Ollama (profile bundled-llm)"
fi

# --- 3. TLS cert for this box ---------------------------------------------------
step "TLS cert"
CBAG_SANS="$SANS" ./scripts/gen-cert.sh

# --- 4. Build images (the ComfyUI/torch build is the slow ~15-30 min step) ------
step "Build images"
docker compose build

# --- 5. Fetch model weights from official sources -------------------------------
step "Fetch models"
./scripts/fetch-models.sh

step "Build complete"
echo "Next:  ./scripts/run.sh"
