#!/usr/bin/env bash
# Fetch CBAG's model weights from their OFFICIAL sources into the docker volumes.
#
# This project redistributes NOTHING — you download each model yourself, from its
# author, under its own license. See MODELS.md. The talking-head models are
# NON-COMMERCIAL:
#   - SVD  (svd_xt_1_1)      : Stability AI Non-Commercial Research Community License (gated)
#   - Sonic (unet.pth, ...)  : CC BY-NC-SA 4.0  (github.com/jixiaozhong/Sonic)
# Permissive: Whisper (MIT), Qwen3-TTS & Kokoro (Apache-2.0), the LLM (its own license).
#
# Idempotent: re-running skips weights already present. Downloads land in the
# `comfyui-models` volume (mounted at /opt/ComfyUI/models) and the Ollama store.
#
#   HF_TOKEN=hf_xxx ./scripts/fetch-models.sh
#   CBAG_ACCEPT_LICENSES=1 HF_TOKEN=hf_xxx ./scripts/fetch-models.sh   # non-interactive
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] && { set -a; . ./.env; set +a; }
LLM_MODEL="${CBAG_LLM_MODEL:-qwen2.5:3b}"
LLM_BASE_URL="${LLM_BASE_URL:-http://host.docker.internal:11434}"
# Official Sonic weights (author's Google Drive, linked from the ComfyUI_Sonic README).
SONIC_DRIVE="${CBAG_SONIC_DRIVE:-https://drive.google.com/drive/folders/1oe8VTPUy0-MHHW2a_NJ1F8xL-0VN5G7W}"
# SVD weights. Default = an ungated HF mirror: the Stability AI Non-Commercial Research
# License explicitly allows non-commercial redistribution on HuggingFace, so no token is
# needed. To pull from Stability's official (gated) repo instead, set:
#   CBAG_SVD_REPO=stabilityai/stable-video-diffusion-img2vid-xt-1-1  HF_TOKEN=hf_xxx
SVD_REPO="${CBAG_SVD_REPO:-vdo/stable-video-diffusion-img2vid-xt-1-1}"
# SHA-256 integrity pins (svd_xt_1_1 is byte-identical across the official + mirror).
# Override CBAG_SVD_SHA256 for a different source, or CBAG_SKIP_SHA256=1 to bypass.
SVD_SHA256="${CBAG_SVD_SHA256:-69ccfea1bb45dd63b3ba8b6cfe8b0d45d780995dfdde590aeaa97cc567018d33}"

say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

# Run a shell snippet inside a throwaway comfyui container; the comfyui-models
# volume is mounted at /opt/ComfyUI/models, so downloads persist.
in_comfy() { docker compose run --rm --no-deps -e HF_TOKEN="${HF_TOKEN:-}" comfyui bash -lc "$1"; }

say "CBAG model fetch"
cat <<'EOF'
You are about to download model weights from their official sources, each under
its own license (see MODELS.md). Note: the talking-head VIDEO pipeline (SVD + Sonic)
is licensed for NON-COMMERCIAL use only. Text and voice models are permissive.
EOF
if [ "${CBAG_ACCEPT_LICENSES:-}" != "1" ]; then
  read -rp "Proceed and accept these model licenses? [y/N] " a
  [ "$a" = "y" ] || [ "$a" = "Y" ] || { echo "Aborted."; exit 1; }
fi

# 1) Stable Video Diffusion (svd_xt_1_1) -----------------------------------------
# Default source is ungated (no token). huggingface_hub reads HF_TOKEN from env (passed
# via in_comfy's -e) automatically if you point CBAG_SVD_REPO at the gated official repo.
say "Stable Video Diffusion (svd_xt_1_1)"
echo "Source: ${SVD_REPO}  (Stability AI Non-Commercial Research License)"
in_comfy '
  set -e; D=/opt/ComfyUI/models/checkpoints; mkdir -p "$D"
  if [ -s "$D/svd_xt_1_1.safetensors" ]; then echo "SVD present — skip"; exit 0; fi
  python3 -c "from huggingface_hub import hf_hub_download; hf_hub_download(\"'"${SVD_REPO}"'\", \"svd_xt_1_1.safetensors\", local_dir=\"$D\")"'

# 2) Sonic weights (official Google Drive) + Whisper-tiny (official HF) ------------
say "Sonic talking-head weights"
in_comfy '
  set -e; cd /opt/ComfyUI/models
  if [ -s sonic/unet.pth ]; then echo "Sonic present — skip"; else
    pip install --break-system-packages -q gdown
    rm -rf sonic_dl; python3 -m gdown --folder "'"${SONIC_DRIVE}"'" -O sonic_dl
    mkdir -p sonic
    # The Drive folder nests the core weights under a "Sonic/" subdir while
    # yoloface_v5m.pt + RIFE/ sit at the root. Flatten the leading "Sonic/" so the
    # node sees sonic/{unet.pth,audio2token.pth,audio2bucket.pth,yoloface_v5m.pt,RIFE/}.
    ( cd sonic_dl && find . -type f | while read -r f; do
        rel=${f#./}; rel=${rel#Sonic/}
        mkdir -p "../sonic/$(dirname "$rel")"; cp -n "$f" "../sonic/$rel"
      done )
    rm -rf sonic_dl
  fi
  if [ ! -s sonic/whisper-tiny/model.safetensors ]; then
    python3 -c "from huggingface_hub import snapshot_download; \
snapshot_download(\"openai/whisper-tiny\", local_dir=\"sonic/whisper-tiny\")"
  fi
  echo "Sonic files:"; ls -1 sonic 2>/dev/null'

# 2b) Verify integrity of the fetched weights (pickle .pth files load arbitrary code,
#     so a tampered download = code execution — fail hard on any mismatch).
say "Verify checksums (SHA-256)"
if [ -n "${CBAG_SKIP_SHA256:-}" ]; then
  echo "skipped (CBAG_SKIP_SHA256 set)"
else
  in_comfy '
    set -e; cd /opt/ComfyUI/models
    printf "%s\n" \
      "'"${SVD_SHA256}"'  checkpoints/svd_xt_1_1.safetensors" \
      "2fb0b0b8fe07232f9c4e8af4ce64fc3b33593bf6dfd7c840b60585dc6017128b  sonic/unet.pth" \
      "68cf305813bf5e4682c4f6a80955233cfad6a5e194fd4a6963f27e4e8ee490d8  sonic/audio2token.pth" \
      "4af942fded37b70d0a0a7993b8c0f46b5b1e104bcf7b6316f7b509900db69d26  sonic/audio2bucket.pth" \
      "5ef5928d2ee1350ea7050ad7524b26a2b55e5c69fee49cd499667bde6a215b17  sonic/yoloface_v5m.pt" \
      "fe854fc8996547c953f732aaa3b78cae76cc0a12833ae856ea0749c4c570d7d8  sonic/RIFE/flownet.pkl" \
      | sha256sum -c -' \
    || { echo "!! checksum verification FAILED — refusing to continue (delete the bad file and re-run)"; exit 1; }
  echo "checksums OK"
fi

# 3) Qwen3-TTS (voice cloning) — lazy, official Qwen repos ------------------------
say "Qwen3-TTS (voice cloning)"
echo "Downloads from the official Qwen/ repos on the FIRST voice-clone request"
echo "(~4 GB, one-time, Apache-2.0). The default Kokoro voices work immediately."

# 4) LLM (stage-2 text refinement only) ------------------------------------------
say "LLM: $LLM_MODEL"
case "$LLM_BASE_URL" in
  *llm:11434*)
    echo "Pulling into the bundled Ollama..."
    docker compose --profile bundled-llm up -d llm
    docker compose exec -T llm ollama pull "$LLM_MODEL" ;;
  *)
    # From this shell the host Ollama is on localhost (host.docker.internal is the
    # name the *backend container* uses, and doesn't resolve here).
    HU="${LLM_BASE_URL/host.docker.internal/localhost}"
    echo "Pulling into the host Ollama ($HU)..."
    if command -v ollama >/dev/null 2>&1; then ollama pull "$LLM_MODEL"
    else curl -fsS "${HU}/api/pull" -d "{\"name\":\"${LLM_MODEL}\",\"stream\":false}" >/dev/null && echo "pulled via API"; fi ;;
esac

say "All models provisioned."
