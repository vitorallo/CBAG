"""CBAG TTS service (stage 3) — default voices via Kokoro.

Synthesizes a script to WAV using pre-baked male/female default voices. Voice
cloning (advanced/optional) is added later via a heavier engine; this service
covers the primary, low-resource default-voice path.
"""
import io
import os
import subprocess

import soundfile as sf
from fastapi import FastAPI, HTTPException, Response
from kokoro_onnx import Kokoro
from pydantic import BaseModel, Field

from storage import job_artifact_dir
from voices import DEFAULT_VOICES, resolve_voice

MODEL = os.environ.get("KOKORO_MODEL", "/models/kokoro-v1.0.onnx")
VOICES_BIN = os.environ.get("KOKORO_VOICES", "/models/voices-v1.0.bin")
ARTIFACT_ROOT = os.environ.get("ARTIFACT_ROOT", "/artifacts")

app = FastAPI(title="CBAG tts — Kokoro default voices")
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = Kokoro(MODEL, VOICES_BIN)
    return _engine


def gpu_info():
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return {"available": True, "gpus": [l for l in out.stdout.splitlines() if l.strip()]}
        return {"available": False, "error": out.stderr.strip()}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)}


@app.on_event("startup")
def _warm():
    try:
        engine()
    except Exception:  # noqa: BLE001 - health still reports; first synth retries
        pass


class SynthRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = "female"          # "male" | "female" | raw Kokoro voice id
    speed: float = Field(1.0, ge=0.5, le=2.0)
    job_id: str | None = None      # if set, also write to <ARTIFACT_ROOT>/<job_id>/speech.wav


@app.get("/health")
def health():
    ready = os.path.exists(MODEL) and os.path.exists(VOICES_BIN)
    return {
        "status": "ok" if ready else "loading",
        "service": "tts",
        "engine": "kokoro",
        "default_voices": list(DEFAULT_VOICES),
        "gpu": gpu_info(),
    }


@app.get("/voices")
def voices():
    return {"default_voices": DEFAULT_VOICES}


@app.post("/synthesize")
def synthesize(req: SynthRequest):
    voice_id = resolve_voice(req.voice)
    samples, sample_rate = engine().create(req.text, voice=voice_id, speed=req.speed, lang="en-us")

    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    data = buf.getvalue()

    if req.job_id:
        try:
            out_dir = job_artifact_dir(ARTIFACT_ROOT, req.job_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid job_id")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "speech.wav"), "wb") as fh:
            fh.write(data)

    return Response(
        content=data,
        media_type="audio/wav",
        headers={"X-Voice": voice_id, "X-Sample-Rate": str(sample_rate)},
    )
