"""CBAG backend — bootstrap-infra skeleton.

Exposes its own health endpoint and an aggregate health check that pings each
model service, proving the cross-service wiring works before any model logic
exists.
"""
import asyncio
import logging
import os
import struct
from typing import List, Optional

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import settings
from .jobs import manager, retention_sweeper, run_job, sse
from .pipeline import bs_core, refine as refine_mod

FRONTEND_DIR = os.environ.get(
    "FRONTEND_DIR", os.path.join(os.path.dirname(__file__), "..", "frontend")
)

MIN_PORTRAIT_PX = int(os.environ.get("MIN_PORTRAIT_PX", "384"))


def _image_min_side(data):
    """min(width,height) for PNG/JPEG bytes, or None if the format is unknown."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return min(w, h)
        if data[:2] == b"\xff\xd8":  # JPEG
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", data[i + 3:i + 7])
                    return min(w, h)
                if marker == 0xD8 or marker == 0xD9 or 0xD0 <= marker <= 0xD7:
                    continue
                i += struct.unpack(">H", data[i:i + 2])[0]
    except Exception:  # noqa: BLE001
        return None
    return None

logger = logging.getLogger("cbag")

app = FastAPI(title="Corporate Bullshit Agentic Generator — Backend")

# Permissive CORS so the SPA can also be hosted off-box (e.g. the Mac) if desired.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
async def _start_sweeper():
    asyncio.create_task(retention_sweeper())

# Health probes per service. Ollama answers on /api/tags; the model services
# answer on /health.
SERVICE_HEALTH = {
    "llm": f"{settings.llm_base_url}/api/tags",
    "tts": f"{settings.tts_base_url}/health",
    "video": f"{settings.video_base_url}/health",
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "backend"}


@app.get("/health/services")
async def health_services():
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICE_HEALTH.items():
            try:
                r = await client.get(url)
                results[name] = {"ok": r.status_code == 200, "code": r.status_code}
            except Exception as exc:  # noqa: BLE001 - report any failure verbatim
                results[name] = {"ok": False, "error": str(exc)}
    overall = all(v.get("ok") for v in results.values())
    return {"status": "ok" if overall else "degraded", "services": results}


@app.get("/")
def index():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="frontend not found")


@app.get("/info")
def info():
    return {
        "app": "Corporate Bullshit Agentic Generator (CBAG)",
        "stage": "web-app-ui",
        "services": list(SERVICE_HEALTH.keys()),
    }


class GenerateRequest(BaseModel):
    length: int = Field(3, ge=1, le=50, description="Number of sentences")
    density: float = Field(0.5, ge=0.0, le=1.0, description="Buzzword density")
    topic_seeds: Optional[List[str]] = Field(None, description="Bias toward a topic")
    seed: Optional[int] = Field(None, description="Deterministic seed")


@app.post("/generate")
def generate(req: GenerateRequest):
    """Stage 1 (BS core): raw buzzword text from the grammar."""
    text = bs_core.generate(
        length=req.length,
        density=req.density,
        topic_seeds=req.topic_seeds,
        seed=req.seed,
    )
    return {"text": text}


class RefineRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    topic: Optional[str] = None
    persona: Optional[str] = None
    length: Optional[str] = None


@app.post("/refine")
async def refine(req: RefineRequest):
    """Stage 2 (LLM): rewrite raw BS into a persona-driven monologue."""
    try:
        return await refine_mod.refine(
            req.raw_text, topic=req.topic, persona=req.persona, length=req.length
        )
    except Exception as exc:  # noqa: BLE001 - log detail, return a generic message
        logger.warning("refine failed: %s", exc)
        raise HTTPException(status_code=502, detail="LLM refinement failed")


@app.get("/personas")
def personas():
    return {"personas": list(refine_mod.PERSONAS), "lengths": list(refine_mod.LENGTH_GUIDE)}


# --- Pipeline orchestration (stage 5) ---

@app.post("/api/jobs")
async def create_job(
    topic: Optional[str] = Form(None),
    persona: Optional[str] = Form(None),
    length: Optional[str] = Form(None),
    voice: str = Form("female"),
    face: str = Form("man"),          # man | woman default face, or uploaded photo
    quality: str = Form("fast"),      # fast (Sonic) | hd (later)
    text_only: bool = Form(False),
    video: bool = Form(True),          # render the talking-head video (else stop after voice)
    consent: bool = Form(False),
    seed: Optional[int] = Form(None),
    photo: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None),   # reference audio for cloning
):
    """Submit a pipeline job (multipart: optional portrait photo + fields)."""
    make_video = video and not text_only
    # The portrait/consent only matter when we actually render a video.
    use_photo = photo is not None and bool(photo.filename) and make_video
    if use_photo and not consent:
        raise HTTPException(status_code=400, detail="consent required to use an uploaded photo")

    # Validate an uploaded portrait before creating the job (reject too-low-res).
    photo_bytes = None
    photo_ext = ".jpg"
    if use_photo:
        photo_bytes = await photo.read()
        min_side = _image_min_side(photo_bytes)
        if min_side is not None and min_side < MIN_PORTRAIT_PX:
            raise HTTPException(
                status_code=400,
                detail=f"portrait too low-resolution ({min_side}px on the short side); "
                       f"use a clear, front-facing photo of at least {MIN_PORTRAIT_PX}px (ideally 512px+)",
            )
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            photo_ext = ext

    # Voice sample (reference audio) for cloning — only used when not text_only.
    has_sample = voice_sample is not None and bool(voice_sample.filename) and not text_only
    sample_bytes = None
    sample_ext = ".webm"
    if has_sample:
        sample_bytes = await voice_sample.read()
        ext = os.path.splitext(voice_sample.filename)[1].lower()
        if ext in (".webm", ".wav", ".mp3", ".m4a", ".ogg"):
            sample_ext = ext

    inputs = {
        "topic": topic, "persona": persona, "length": length, "voice": voice,
        "face": face, "quality": quality, "text_only": text_only,
        "video": make_video, "clone": has_sample, "seed": seed,
    }
    job = manager.create(inputs)

    out_dir = os.path.join(settings.artifact_root, job.id)
    if photo_bytes is not None or sample_bytes is not None:
        os.makedirs(out_dir, exist_ok=True)
    if photo_bytes is not None:
        with open(os.path.join(out_dir, "portrait" + photo_ext), "wb") as fh:
            fh.write(photo_bytes)
    if sample_bytes is not None:
        with open(os.path.join(out_dir, "voice_sample" + sample_ext), "wb") as fh:
            fh.write(sample_bytes)

    asyncio.create_task(run_job(job))
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.public()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    async def gen():
        q = job.subscribe()
        try:
            sent = 0
            for ev in job.history():
                sent = ev["seq"]
                yield sse(ev)
            if job.is_terminal():
                return
            while True:
                ev = await q.get()
                if ev["seq"] <= sent:
                    continue
                sent = ev["seq"]
                yield sse(ev)
                if ev["type"] in ("completed", "failed"):
                    break
        finally:
            job.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/text")
def job_text(job_id: str):
    job = manager.get(job_id)
    if not job or "text" not in job.artifacts:
        raise HTTPException(status_code=404, detail="no text")
    return PlainTextResponse(job.artifacts["text"])


@app.get("/api/jobs/{job_id}/audio")
def job_audio(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    path = os.path.join(settings.artifact_root, job_id, "speech.wav")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no audio")
    return FileResponse(path, media_type="audio/wav", filename="speech.wav")


@app.get("/api/jobs/{job_id}/progress")
def job_progress(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    path = os.path.join(settings.artifact_root, job_id, "progress.json")
    if os.path.exists(path):
        import json
        try:
            with open(path) as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            pass
    return {"pct": 0, "elapsed": 0}


@app.get("/api/jobs/{job_id}/video")
def job_video(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    path = os.path.join(settings.artifact_root, job_id, "video.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no video")
    return FileResponse(path, media_type="video/mp4", filename="cbag.mp4")
