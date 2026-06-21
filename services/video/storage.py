"""Safe artifact-path resolution for the video service (pure, testable).

Mirrors services/tts/storage.py — client-supplied job_id must never be trusted
to build a filesystem path.
"""
import os
import re

_JOB_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def job_artifact_dir(root, job_id):
    if not job_id or not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("invalid job_id")
    base = os.path.realpath(root)
    out = os.path.realpath(os.path.join(base, job_id))
    if out != base and not out.startswith(base + os.sep):
        raise ValueError("invalid job_id")
    return out
