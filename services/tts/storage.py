"""Safe artifact-path resolution (pure, testable).

job_id is client-supplied, so it must never be trusted to build a filesystem
path. We allow only a strict charset (no slashes, no dots) and additionally
verify the resolved realpath stays under the artifact root (defense in depth).
"""
import os
import re

_JOB_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def job_artifact_dir(root, job_id):
    """Return the safe artifact dir for job_id under root, or raise ValueError."""
    if not job_id or not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("invalid job_id")
    base = os.path.realpath(root)
    out = os.path.realpath(os.path.join(base, job_id))
    if out != base and not out.startswith(base + os.sep):
        raise ValueError("invalid job_id")
    return out
