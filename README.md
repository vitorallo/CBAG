# Corporate Bullshit Agentic Generator (CBAG)

A local, GPU-native demo for the **NVIDIA DGX Spark / Dell GB10**. Pick a topic and a
persona; CBAG generates buzzword nonsense, rewrites it into a coherent corporate
monologue with a local LLM, speaks it aloud, and animates a portrait into a lip-synced
**talking-head video** of someone delivering it — optionally in *your* cloned voice.

Four-stage pipeline — **buzzword grammar → LLM refine → TTS (default or cloned voice) →
talking-head video** — behind a small web app. **100 % local, no cloud, no API tokens.**

> **Non-commercial demo.** The talking-head video uses Stable Video Diffusion and Sonic,
> which are licensed for **non-commercial use only**. See [MODELS.md](MODELS.md).

## Hardware & prerequisites

- **NVIDIA DGX Spark / Dell GB10** (Grace Blackwell, aarch64, 128 GB unified memory),
  DGX OS / Ubuntu 24.04, **CUDA 13**.
- **Docker + Compose v2 + NVIDIA Container Toolkit** (GPU passthrough).
- **~50 GB free disk** (images + model weights) and internet for the first install.
- **No Hugging Face token required** — Stable Video Diffusion is fetched from an ungated,
  license-permitted mirror (its non-commercial license explicitly allows HF redistribution).
  To pull from Stability's official *gated* repo instead: `CBAG_SVD_REPO=stabilityai/stable-video-diffusion-img2vid-xt-1-1 HF_TOKEN=hf_xxx ./scripts/build.sh`.

## Quickstart

```bash
git clone https://github.com/vitorallo/CBAG.git && cd CBAG
./scripts/build.sh    # preflight + auto-configure this box + build + fetch weights
./scripts/run.sh      # start; prints https://<your-box-ip>:8443
```

`run.sh` prints the URL — e.g. `https://<your-box-ip>:8443`. First visit shows a
self-signed-cert warning → **Advanced → Proceed** (HTTPS is required for the microphone).
Stop with `./scripts/down.sh` (add `--purge` to also drop the model volumes).

Everything **builds on the box** — no prebaked images, no bundled weights. Each model is
downloaded from its **official source** under its own license (see [MODELS.md](MODELS.md)).

## What it does

1. **Buzzword grammar** — a port of the classic generator (deterministic, no GPU); the seed.
2. **LLM refine** — a local Ollama model rewrites it into an on-persona monologue
   (visionary CEO, McKinsey consultant, startup founder, thought leader). *Text only —
   swapping the model changes only this stage.*
3. **Voice** — Kokoro default voices, or **clone your own** from a ~10 s recording/upload (Qwen3-TTS).
4. **Talking-head video** — ComfyUI + Sonic + Stable Video Diffusion animate a portrait
   (default face, or your upload) to lip-sync the speech.

## Services & ports

| Service | Port | Role |
|---------|------|------|
| `caddy` | 80 → **8443** | HTTPS edge (self-signed); secure context for the mic. 443 is often the Dell demo. |
| `backend` | 8000 | FastAPI orchestrator (CPU) + the web app + SSE progress |
| `tts` | 8100 | Kokoro default voices |
| `video` | 8200 | drives ComfyUI for talking-head render **and** voice cloning |
| `comfyui` | 8188 | ComfyUI engine (Sonic + SVD + Qwen3-TTS), cu130 torch |
| `llm` | 11434 | Ollama — reuses a host Ollama if present, else a bundled container |

## Configuration

`build.sh` writes `.env` for you (detected IPs, cert SANs, LLM source). Override anything
in `.env` (see [.env.example](.env.example)): `CBAG_LLM_MODEL` (default `qwen2.5:3b`,
small/fast/Apache-2.0 — use `gpt-oss:20b` for richer prose), `CBAG_HOST`, `CBAG_SANS`,
`CBAG_HTTPS_PORT`.

## Troubleshooting

- **Port 443 in use** — expected (Dell demo); CBAG serves HTTPS on **8443**.
- **SVD download fails** — the default mirror needs no token; if you set `CBAG_SVD_REPO` to the gated repo, accept its license while logged in to HF and export a valid `HF_TOKEN`.
- **First voice-clone is slow** — Qwen3-TTS (~4 GB) downloads once on first use; default voices are instant.
- **Mic blocked** — you must use the **https://** URL (a secure context), not `http://…:8000`.

## Project layout

`backend/` FastAPI orchestrator + SPA · `services/` model services (`tts`, `video`,
`comfyui`, `caddy`) · `frontend/` the web app · `scripts/` build/run/fetch-models ·
`playbook/cbag/` the DGX Spark playbook entry points · `MODELS.md` model sources + licenses.
