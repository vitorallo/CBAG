"""CBAG video service (stage 4) — talking-head generation.

Single portrait + audio -> lip-synced MP4, behind a pluggable VideoBackend
registry with quality tiers. This is the model-agnostic scaffold: the registry
is empty until a modern backend is installed (the talking-head-video impl step).
SadTalker (2023, old CUDA) is intentionally NOT used — backends target recent
PyTorch on the NGC aarch64+CUDA base so they run on Blackwell.
"""
import glob
import os
import subprocess

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from storage import job_artifact_dir
from comfyui_sonic import render as comfyui_sonic_render
from comfyui_clone import clone as comfyui_clone

ARTIFACT_ROOT = os.environ.get("ARTIFACT_ROOT", "/artifacts")

# backend name -> render callable(image_path, audio_path, out_path, opts).
BACKENDS = {"comfyui-sonic": comfyui_sonic_render}
# quality tier -> backend name. (hd -> hallo3 later; for now both use Sonic.)
QUALITY_TIERS = {"fast": "comfyui-sonic", "hd": "comfyui-sonic"}

app = FastAPI(title="CBAG video — talking-head")


def gpu_info():
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return {"available": True, "gpus": [l for l in out.stdout.splitlines() if l.strip()]}
        return {"available": False, "error": out.stderr.strip()}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video",
        "backends": list(BACKENDS),
        "gpu": gpu_info(),
    }


@app.get("/backends")
def backends():
    return {"backends": list(BACKENDS), "quality_tiers": QUALITY_TIERS}


DEFAULT_FACES_DIR = os.environ.get("DEFAULT_FACES_DIR", "/app/default_faces")


class RenderRequest(BaseModel):
    job_id: str
    backend: str | None = None      # explicit backend, or resolve from quality
    quality: str = "fast"           # fast | hd
    face: str = "man"               # default face (man|woman) if no portrait uploaded


def _resolve_backend(req):
    if req.backend:
        if req.backend not in BACKENDS:
            raise HTTPException(status_code=400, detail=f"unknown backend '{req.backend}'")
        return req.backend
    return QUALITY_TIERS.get(req.quality)


@app.post("/render")
def render(req: RenderRequest):
    if not BACKENDS:
        raise HTTPException(
            status_code=503,
            detail="no video backend installed yet (talking-head-video in progress)",
        )
    try:
        out_dir = job_artifact_dir(ARTIFACT_ROOT, req.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid job_id")

    audio = os.path.join(out_dir, "speech.wav")
    if not os.path.exists(audio):
        raise HTTPException(status_code=404, detail="missing audio for job")

    # Use an uploaded portrait if present, else fall back to a default face.
    portraits = sorted(glob.glob(os.path.join(out_dir, "portrait.*")))
    if portraits:
        image = portraits[0]
    else:
        face = req.face if req.face in ("man", "woman") else "man"
        image = os.path.join(DEFAULT_FACES_DIR, f"{face}.jpg")
        if not os.path.exists(image):
            raise HTTPException(status_code=404, detail="no portrait and no default face")

    backend_name = _resolve_backend(req)
    if not backend_name:
        raise HTTPException(status_code=400, detail=f"no backend for quality '{req.quality}'")

    out_path = os.path.join(out_dir, "video.mp4")
    try:
        BACKENDS[backend_name](image, audio, out_path, req.model_dump())
    except Exception as exc:  # noqa: BLE001 - clean failure, no partial file
        if os.path.exists(out_path):
            os.remove(out_path)
        raise HTTPException(status_code=500, detail=f"render failed ({backend_name}): {exc}")

    return {"video": f"{req.job_id}/video.mp4", "backend": backend_name}


class CloneRequest(BaseModel):
    job_id: str
    text: str


@app.post("/clone")
def clone(req: CloneRequest):
    """Synthesize `text` in the voice from the job's uploaded sample -> speech.wav."""
    try:
        out_dir = job_artifact_dir(ARTIFACT_ROOT, req.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid job_id")
    if not (req.text or "").strip():
        raise HTTPException(status_code=400, detail="empty text")
    samples = sorted(glob.glob(os.path.join(out_dir, "voice_sample.*")))
    if not samples:
        raise HTTPException(status_code=404, detail="no voice sample for job")

    out_wav = os.path.join(out_dir, "speech.wav")
    try:
        comfyui_clone(samples[0], req.text, out_wav)
    except Exception as exc:  # noqa: BLE001 - clean failure
        raise HTTPException(status_code=500, detail=f"clone failed: {exc}")
    return {"audio": f"{req.job_id}/speech.wav"}
