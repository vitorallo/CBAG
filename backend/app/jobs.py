"""CBAG job orchestration (stage 5).

Runs one pipeline job through ordered stages — generate -> refine -> voice ->
video — asynchronously, emitting per-stage events for SSE progress, storing
artifacts under <ARTIFACT_ROOT>/<job_id>/, and failing cleanly. The video stage
is a placeholder until the talking-head-video epic lands.
"""
import asyncio
import json
import os
import shutil
import time
import uuid

from .config import settings
from .pipeline import bs_core, refine as refine_mod, tts as tts_client, video as video_client


def sse(event):
    return f"data: {json.dumps(event)}\n\n"


class Job:
    def __init__(self, inputs):
        self.id = uuid.uuid4().hex
        self.inputs = inputs or {}
        self.status = "queued"          # queued | running | completed | failed
        self.stage = None               # generate | refine | voice | video | done
        self.error = None
        self.artifacts = {}
        self.created = time.time()
        self._events = []
        self._seq = 0
        self._subs = []                 # list[asyncio.Queue]

    def emit(self, type, **data):
        self._seq += 1
        ev = {
            "seq": self._seq,
            "ts": round(time.time(), 3),
            "type": type,
            "stage": self.stage,
            "status": self.status,
            **data,
        }
        self._events.append(ev)
        for q in self._subs:
            q.put_nowait(ev)
        return ev

    def subscribe(self):
        q = asyncio.Queue()
        self._subs.append(q)
        return q

    def unsubscribe(self, q):
        if q in self._subs:
            self._subs.remove(q)

    def history(self):
        return list(self._events)

    def is_terminal(self):
        return self.status in ("completed", "failed")

    def public(self):
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "error": self.error,
            "artifacts": self.artifacts,
            "created": self.created,
        }


class JobManager:
    def __init__(self):
        self._jobs = {}

    def create(self, inputs):
        job = Job(inputs)
        self._jobs[job.id] = job
        return job

    def get(self, job_id):
        return self._jobs.get(job_id)

    def all(self):
        return list(self._jobs.values())

    def remove(self, job_id):
        self._jobs.pop(job_id, None)


manager = JobManager()


def _artifact_dir(job_id):
    d = os.path.join(settings.artifact_root, job_id)
    os.makedirs(d, exist_ok=True)
    return d


async def run_job(job):
    """Execute the pipeline stages in order, emitting progress events."""
    job.status = "running"
    inp = job.inputs
    try:
        # Stage 1 — generate (in-process, CPU)
        job.stage = "generate"
        job.emit("stage_start")
        topic = inp.get("topic")
        raw = bs_core.generate(
            length=3,
            density=0.6,
            topic_seeds=(topic.split() if topic else None),
            seed=inp.get("seed"),
        )
        job.artifacts["raw"] = raw
        job.emit("stage_done", preview=raw[:140])

        # Stage 2 — refine (LLM)
        job.stage = "refine"
        job.emit("stage_start")
        result = await refine_mod.refine(
            raw, topic=topic, persona=inp.get("persona"), length=inp.get("length")
        )
        text = result["text"]
        out_dir = _artifact_dir(job.id)
        with open(os.path.join(out_dir, "monologue.txt"), "w") as fh:
            fh.write(text)
        job.artifacts["text"] = text
        job.artifacts["persona"] = result.get("persona")
        job.emit("stage_done", preview=text[:140])

        if inp.get("text_only"):
            job.status = "completed"
            job.stage = "done"
            job.emit("completed")
            return

        # Stage 3 — voice. Clone the uploaded sample if provided, else default TTS.
        job.stage = "voice"
        job.emit("stage_start")
        if inp.get("clone"):
            await video_client.clone(job.id, text)
        else:
            await tts_client.synthesize(
                text=text, voice=inp.get("voice", "female"), job_id=job.id
            )
        job.artifacts["audio"] = f"{job.id}/speech.wav"
        job.emit("stage_done")

        # Stage 4 — video (talking-head), only when requested.
        if inp.get("video", True):
            job.stage = "video"
            job.emit("stage_start")
            await video_client.render(
                job.id, quality=inp.get("quality", "fast"), face=inp.get("face", "man")
            )
            job.artifacts["video"] = f"{job.id}/video.mp4"
            job.emit("stage_done")

        job.status = "completed"
        job.stage = "done"
        job.emit("completed")
    except Exception as exc:  # noqa: BLE001 - fail the job cleanly with context
        job.status = "failed"
        job.error = f"{job.stage}: {exc}"
        job.emit("failed", error=str(exc))


async def retention_sweeper():
    """Periodically drop jobs + artifacts older than the configured TTL."""
    ttl = settings.artifact_ttl_seconds
    interval = min(3600, max(60, ttl // 10))
    while True:
        await asyncio.sleep(interval)
        now = time.time()
        for job in manager.all():
            if now - job.created > ttl:
                shutil.rmtree(
                    os.path.join(settings.artifact_root, job.id), ignore_errors=True
                )
                manager.remove(job.id)
