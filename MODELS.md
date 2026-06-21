# Models, sources & licenses

CBAG **redistributes no model weights.** `scripts/fetch-models.sh` downloads each model
from its **official source** onto your box, under its own license. By running it you accept
those licenses. Nothing here is bundled into an image or committed to this repo.

## ⚠️ The talking-head video pipeline is NON-COMMERCIAL

Two of the models are licensed for **non-commercial use only**, so **CBAG with video is a
non-commercial demo.** The text and voice stages are permissive (you could run those
commercially), but the talking-head video must not be used commercially.

## Ledger

| Model | Stage | Official source | License | Commercial? |
|-------|-------|-----------------|---------|-------------|
| **Stable Video Diffusion** (`svd_xt_1_1`) | Video | `vdo/stable-video-diffusion-img2vid-xt-1-1` (ungated mirror; or the gated [stabilityai/…](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt-1-1) via `CBAG_SVD_REPO`+`HF_TOKEN`) | Stability AI Non-Commercial Research Community License | ❌ No |
| **Sonic** (`unet.pth`, `audio2token`, `audio2bucket`, `yoloface_v5m`, `RIFE`) | Video | [github.com/jixiaozhong/Sonic](https://github.com/jixiaozhong/Sonic) (weights via the author's Google Drive) | **CC BY-NC-SA 4.0** | ❌ No |
| **Whisper-tiny** | Video (Sonic aux) | [openai/whisper-tiny](https://huggingface.co/openai/whisper-tiny) | MIT | ✅ Yes |
| **Qwen3-TTS** (12Hz 1.7B/0.6B) | Voice clone | [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) (+ tokenizer) | Apache-2.0 | ✅ Yes |
| **Kokoro** (`kokoro-v1.0.onnx`) | Voice (default) | [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) releases | Apache-2.0 | ✅ Yes |
| **LLM** (`qwen2.5:3b` default) | Text refine | [Ollama library](https://ollama.com/library/qwen2.5) / Hugging Face | Apache-2.0 | ✅ Yes |

Notes:
- **SVD source:** the default is an **ungated mirror** — the Stability Non-Commercial Research
  License *explicitly* permits non-commercial redistribution on HuggingFace (*"distributing the
  Models on HuggingFace is not a violation"*), so no token or gate is needed. To pull from the
  official **gated** repo instead, set `CBAG_SVD_REPO=stabilityai/stable-video-diffusion-img2vid-xt-1-1`
  + an `HF_TOKEN` (after accepting its license while logged in to HF). **Non-commercial only**, either way.
- **Sonic** weights come from the authors' official distribution (the Google Drive linked in
  the `ComfyUI_Sonic` node README). CC BY-NC-SA requires **attribution** and **ShareAlike**:
  *Sonic — Xiaozhong Ji et al., Tencent (CVPR 2025), https://github.com/jixiaozhong/Sonic.*
- **Kokoro** is fetched at image-build time from its official GitHub release (on the box).
- The default **LLM** only drives stage-2 text refinement; swap it via `CBAG_LLM_MODEL`
  (e.g. `gpt-oss:20b`). Each LLM carries its own license.
- **Integrity:** `fetch-models.sh` verifies the **SHA-256** of every fetched SVD + Sonic file
  and refuses to continue on a mismatch. The Sonic weights are pickle (`*.pth`/`*.pkl`) that
  `torch.load` executes, so a tampered download = code execution — the checksum gate blocks
  that before anything is loaded. Override a hash with `CBAG_SVD_SHA256`; bypass (not advised)
  with `CBAG_SKIP_SHA256=1`.

## Where weights land

- ComfyUI models → the `comfyui-models` docker volume
  (`checkpoints/svd_xt_1_1.safetensors`, `sonic/…`, `TTS/Qwen3-TTS/…`).
- LLM → the Ollama store (host Ollama, or the `ollama-models` volume when bundled).
- Kokoro + default faces → baked into the `tts` / `video` images at build time.
