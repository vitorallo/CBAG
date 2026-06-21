"""ComfyUI + Sonic backend for the CBAG video service.

Drives the ComfyUI HTTP API to render a talking-head MP4 from a portrait + audio
using the Sonic node (audio-driven portrait animation) on top of Stable Video
Diffusion. Modern, Blackwell-compatible (cu130 torch) — no 2023-era SadTalker.

Flow: upload portrait + audio to ComfyUI -> submit the Sonic workflow -> poll
history -> download the resulting MP4 to the shared artifact path.
"""
import json
import os
import threading
import time
import wave

import httpx

COMFY = os.environ.get("COMFY_URL", "http://comfyui:8188")
SVD_CKPT = os.environ.get("SONIC_SVD_CKPT", "svd_xt_1_1.safetensors")
# Balanced for speed WITHOUT breaking lip-sync: keep fps high (lip-sync timing
# depends on it), trim resolution + steps (image stayed sharp at 448). The big
# win is the short (1-sentence) monologue = far fewer frames.
DEFAULT_STEPS = int(os.environ.get("SONIC_STEPS", "12"))
DEFAULT_FPS = float(os.environ.get("SONIC_FPS", "25"))
MIN_RES = int(os.environ.get("SONIC_MIN_RES", "448"))
RENDER_TIMEOUT = float(os.environ.get("VIDEO_RENDER_TIMEOUT", "1800"))


def _audio_duration(path):
    w = wave.open(path)
    return w.getnframes() / float(w.getframerate())


def _upload(client, path):
    with open(path, "rb") as fh:
        files = {"image": (os.path.basename(path), fh, "application/octet-stream")}
        r = client.post(f"{COMFY}/upload/image", files=files, data={"overwrite": "true"})
    r.raise_for_status()
    j = r.json()
    name = j["name"]
    sub = j.get("subfolder") or ""
    return f"{sub}/{name}" if sub else name


def _workflow(image_name, audio_name, duration, steps, fps):
    return {
        "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {"ckpt_name": SVD_CKPT}},
        "2": {"class_type": "SONICTLoader", "inputs": {"model": ["1", 0], "sonic_unet": "unet.pth", "ip_audio_scale": 1.0, "use_interframe": True, "dtype": "fp16"}},
        "3": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "4": {"class_type": "LoadAudio", "inputs": {"audio": audio_name}},
        "5": {"class_type": "SONIC_PreData", "inputs": {"clip_vision": ["1", 1], "vae": ["1", 2], "audio": ["4", 0], "image": ["3", 0], "weight_dtype": ["2", 1], "min_resolution": MIN_RES, "duration": max(1.0, round(duration, 2)), "expand_ratio": 0.5}},
        "6": {"class_type": "SONICSampler", "inputs": {"model": ["2", 0], "data_dict": ["5", 0], "seed": 42, "inference_steps": steps, "dynamic_scale": 1.0, "fps": float(fps)}},
        "7": {"class_type": "CreateVideo", "inputs": {"images": ["6", 0], "fps": ["6", 1], "audio": ["4", 0]}},
        "8": {"class_type": "SaveVideo", "inputs": {"video": ["7", 0], "filename_prefix": "cbag/out", "format": "mp4", "codec": "h264"}},
    }


def _find_video(outputs):
    for out in outputs.values():
        for key in ("videos", "images", "gifs"):
            for item in out.get(key, []) if isinstance(out, dict) else []:
                if isinstance(item, dict) and str(item.get("filename", "")).endswith(".mp4"):
                    return item
    return None


def _write_progress(path, pct, t0):
    try:
        with open(path, "w") as fh:
            json.dump({"pct": max(0, min(100, int(pct))), "elapsed": round(time.time() - t0)}, fh)
    except Exception:  # noqa: BLE001
        pass


# The Sonic node emits no ComfyUI step events, so we report a time-based estimate
# (calibrated: ~30 s of render per second of audio at the quality settings),
# capped at 95% until the render actually finishes (then 100%).
SECS_PER_AUDIO_SEC = float(os.environ.get("VIDEO_SECS_PER_AUDIO_SEC", "16"))
EST_FLOOR = float(os.environ.get("VIDEO_EST_FLOOR", "25"))


def _progress_estimator(path, est_total, stop, t0):
    while not stop.is_set():
        pct = 100.0 * (time.time() - t0) / est_total
        _write_progress(path, min(95, pct), t0)
        stop.wait(2)


def render(image_path, audio_path, out_path, opts):
    """Render a talking-head MP4 to out_path. Raises on any failure."""
    steps = int((opts or {}).get("inference_steps") or DEFAULT_STEPS)
    fps = float((opts or {}).get("fps") or DEFAULT_FPS)
    progress_path = os.path.join(os.path.dirname(out_path), "progress.json")
    t0 = time.time()
    _write_progress(progress_path, 0, t0)
    duration = _audio_duration(audio_path)
    est_total = max(EST_FLOOR, duration * SECS_PER_AUDIO_SEC)

    with httpx.Client(timeout=120.0) as client:
        img_name = _upload(client, image_path)
        aud_name = _upload(client, audio_path)
        wf = _workflow(img_name, aud_name, duration, steps, fps)

        r = client.post(f"{COMFY}/prompt", json={"prompt": wf})
        if r.status_code != 200:
            raise RuntimeError(f"comfyui /prompt {r.status_code}: {r.text[:300]}")
        pid = r.json()["prompt_id"]

        stop = threading.Event()
        estimator = threading.Thread(
            target=_progress_estimator, args=(progress_path, est_total, stop, t0), daemon=True
        )
        estimator.start()

        try:
            deadline = time.time() + RENDER_TIMEOUT
            outputs = None
            while time.time() < deadline:
                time.sleep(3)
                h = client.get(f"{COMFY}/history/{pid}").json()
                if pid in h:
                    status = h[pid].get("status", {})
                    if status.get("status_str") == "error":
                        raise RuntimeError(f"comfyui render error: {status}")
                    outputs = h[pid].get("outputs", {})
                    break
            if outputs is None:
                raise RuntimeError("comfyui render timed out")
        finally:
            stop.set()
            _write_progress(progress_path, 100, t0)

        info = _find_video(outputs)
        if not info:
            raise RuntimeError(f"no mp4 in comfyui outputs: {list(outputs)}")

        vid = client.get(f"{COMFY}/view", params={"filename": info["filename"], "subfolder": info.get("subfolder", ""), "type": info.get("type", "output")})
        vid.raise_for_status()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(vid.content)
    return out_path
