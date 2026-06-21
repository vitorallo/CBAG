"""ComfyUI + Qwen3-TTS voice-clone backend for the CBAG video service.

Clones the speaker in a reference sample and synthesizes the monologue in that
voice, via ComfyUI's AILab_Qwen3TTSVoiceClone node. We use the 1.7B model with
x_vector_only (speaker embedding) — the reference-transcript path needs the Whisper
node, whose torchaudio.save routes through torchcodec, which won't load on our
cu130 stack. ComfyUI's audio save nodes emit flac/mp3/opus (no wav), so we save
flac and convert to wav with ffmpeg.
"""
import os
import subprocess
import time

import httpx

COMFY = os.environ.get("COMFY_URL", "http://comfyui:8188")
CLONE_MODEL_SIZE = os.environ.get("CLONE_MODEL_SIZE", "1.7B")   # 1.7B (quality) | 0.6B (fast)
CLONE_LANGUAGE = os.environ.get("CLONE_LANGUAGE", "English")    # language of the synthesized monologue
CLONE_TIMEOUT = float(os.environ.get("CLONE_TIMEOUT", "900"))


def _to_wav(src, dst):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ar", "16000", "-ac", "1", dst],
        check=True,
    )


def _upload(client, path):
    with open(path, "rb") as fh:
        files = {"image": (os.path.basename(path), fh, "application/octet-stream")}
        r = client.post(f"{COMFY}/upload/image", files=files, data={"overwrite": "true"})
    r.raise_for_status()
    j = r.json()
    sub = j.get("subfolder") or ""
    return f"{sub}/{j['name']}" if sub else j["name"]


def _find_audio(outputs):
    for out in outputs.values():
        for item in (out.get("audio", []) if isinstance(out, dict) else []):
            if isinstance(item, dict) and item.get("filename"):
                return item
    return None


def clone(ref_path, text, out_wav):
    """Clone the voice in ref_path and speak `text`; write a wav to out_wav."""
    work = os.path.dirname(out_wav)
    ref_wav = os.path.join(work, "ref_clone.wav")
    _to_wav(ref_path, ref_wav)   # normalise any format (webm/mp3/...) to wav

    with httpx.Client(timeout=120.0) as client:
        ref_name = _upload(client, ref_wav)
        wf = {
            "1": {"class_type": "LoadAudio", "inputs": {"audio": ref_name}},
            "2": {"class_type": "AILab_Qwen3TTSVoiceClone", "inputs": {
                "target_text": text, "model_size": CLONE_MODEL_SIZE, "language": CLONE_LANGUAGE,
                "reference_audio": ["1", 0], "x_vector_only": True, "unload_models": True}},
            "3": {"class_type": "SaveAudio", "inputs": {"audio": ["2", 0], "filename_prefix": "cbag/clone"}},
        }
        r = client.post(f"{COMFY}/prompt", json={"prompt": wf})
        if r.status_code != 200:
            raise RuntimeError(f"comfyui /prompt {r.status_code}: {r.text[:300]}")
        pid = r.json()["prompt_id"]

        deadline = time.time() + CLONE_TIMEOUT
        outputs = None
        while time.time() < deadline:
            time.sleep(2)
            h = client.get(f"{COMFY}/history/{pid}").json()
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error":
                    raise RuntimeError(f"clone error: {st}")
                outputs = h[pid].get("outputs", {})
                break
        if outputs is None:
            raise RuntimeError("clone timed out")

        info = _find_audio(outputs)
        if not info:
            raise RuntimeError(f"no audio in clone outputs: {list(outputs)}")
        a = client.get(f"{COMFY}/view", params={
            "filename": info["filename"], "subfolder": info.get("subfolder", ""),
            "type": info.get("type", "output")})
        a.raise_for_status()
        flac = os.path.join(work, "clone_out" + os.path.splitext(info["filename"])[1])
        with open(flac, "wb") as fh:
            fh.write(a.content)

    _to_wav(flac, out_wav)
    return out_wav
