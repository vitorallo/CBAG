"""CBAG TTS client (stage 3) — calls the tts service.

Asks the tts service to synthesize text to speech. When job_id is given, the
tts service writes the WAV into the shared artifact volume at
<ARTIFACT_ROOT>/<job_id>/speech.wav, which the backend can then serve.

httpx is imported lazily so importing this module needs no extra deps.
"""
from ..config import settings


async def synthesize(text, voice="female", speed=1.0, job_id=None, timeout=120.0):
    """Synthesize speech via the tts service. Raises on failure (bounded by timeout)."""
    import httpx

    payload = {"text": text, "voice": voice, "speed": speed}
    if job_id:
        payload["job_id"] = job_id
    url = f"{settings.tts_base_url}/synthesize"

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.content  # WAV bytes (also written to the artifact dir when job_id set)
