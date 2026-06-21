# Corporate Bullshit Agentic Generator (CBAG) — DGX Spark playbook

A fully local, GPU-native demo for the **NVIDIA DGX Spark / Dell GB10**: topic + persona →
a coherent corporate monologue (local LLM) → spoken aloud (default or **cloned** voice) →
a **talking-head video** of someone delivering it. Four model families warm at once on one
box; no cloud, no API tokens. A great "the whole multimodal stack fits in 128 GB" demo.

| | |
|---|---|
| **Hardware** | DGX Spark / GB10 (Grace Blackwell, aarch64, 128 GB unified) |
| **Software** | DGX OS / Ubuntu 24.04, CUDA 13, Docker + Compose v2 + NVIDIA Container Toolkit |
| **Disk** | ~50 GB (images + weights) |
| **Time** | ~30–45 min first run (the ComfyUI/torch build + weight downloads) |
| **Licensing** | **Non-commercial** (talking-head models — see `MODELS.md`) |

## Prerequisites

- Internet access for the first install (everything is fetched from official sources).
- **No Hugging Face token needed** — SVD comes from an ungated, license-permitted mirror.
  (Optional: pull from Stability's gated repo with `CBAG_SVD_REPO`+`HF_TOKEN`.)

## Steps

```bash
git clone https://github.com/vitorallo/CBAG.git && cd CBAG
./playbook/cbag/build.sh   # preflight + autoconfig + build + fetch weights
./playbook/cbag/run.sh     # start; prints https://<box-ip>:8443
```

These delegate to the repo's `scripts/build.sh` and `scripts/run.sh` (the canonical entry
points). Open the printed HTTPS URL, accept the self-signed cert once (required so the
microphone works), and generate. Stop with `./scripts/down.sh`.

## Troubleshooting

- **Port 443 busy** — expected on a Spark (the pre-installed Dell demo). CBAG uses **8443**.
- **SVD 401/403** — only if you set `CBAG_SVD_REPO` to the gated repo: accept its license (logged in to HF) and pass a valid `HF_TOKEN`. The default mirror needs neither.
- **First voice-clone slow** — Qwen3-TTS (~4 GB) downloads once on first use; default voices are instant.
- **Talking-head render time** scales with audio length (pick a *short* length for a snappy demo).

## Models & licenses

Everything is downloaded from its official source at install — nothing is redistributed.
See [`../../MODELS.md`](../../MODELS.md). **The talking-head video pipeline (SVD + Sonic) is
non-commercial.**
