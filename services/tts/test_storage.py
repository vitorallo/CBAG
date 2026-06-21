"""Tests for safe artifact-path resolution (path traversal protection).

    python3 services/tts/test_storage.py
    pytest services/tts/test_storage.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from storage import job_artifact_dir  # noqa: E402

ROOT = "/artifacts"


def test_valid_job_id():
    out = job_artifact_dir(ROOT, "job_123-AB")
    assert out == os.path.realpath(os.path.join(ROOT, "job_123-AB"))


def _rejects(job_id):
    try:
        job_artifact_dir(ROOT, job_id)
        return False
    except ValueError:
        return True


def test_rejects_traversal():
    assert _rejects("../etc")
    assert _rejects("../../etc/passwd")
    assert _rejects("a/../../b")


def test_rejects_slash_and_dots():
    assert _rejects("foo/bar")
    assert _rejects("..")
    assert _rejects("a.b")            # dots not allowed by charset


def test_rejects_empty_and_none():
    assert _rejects("")
    assert _rejects(None)


def test_rejects_too_long():
    assert _rejects("x" * 65)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            fails += 1; print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(fns) - fails}/{len(fns)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(_run())
