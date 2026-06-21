"""CBAG video client (stage 4) — calls the video service to render the MP4.

The video service reads the portrait (or a default face) + speech.wav from the
shared artifact volume (by job_id) and writes <ARTIFACT_ROOT>/<job_id>/video.mp4.
httpx is imported lazily so importing this module needs no extra deps.
"""
from ..config import settings


async def render(job_id, quality="fast", face="man", timeout=1800.0):
    """Render a talking-head video via the video service. Raises on failure."""
    import httpx

    payload = {"job_id": job_id, "quality": quality, "face": face}
    url = f"{settings.video_base_url}/render"

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def clone(job_id, text, timeout=900.0):
    """Synthesize `text` in the job's cloned voice -> speech.wav. Raises on failure.

    The video service hosts the ComfyUI/Qwen3-TTS clone (same engine as Sonic),
    reading <job_id>/voice_sample.* and writing <job_id>/speech.wav.
    """
    import httpx

    payload = {"job_id": job_id, "text": text}
    url = f"{settings.video_base_url}/clone"

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
