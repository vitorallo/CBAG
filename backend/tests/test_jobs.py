"""Unit tests for the Job event/state machine (pure, no network).

    python3 backend/tests/test_jobs.py
    pytest backend/tests/test_jobs.py
"""
import asyncio
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.jobs import Job, JobManager, sse  # noqa: E402


def test_seq_increments_and_history():
    j = Job({"text_only": True})
    j.status = "running"
    e1 = j.emit("stage_start")
    e2 = j.emit("stage_done")
    assert e1["seq"] == 1 and e2["seq"] == 2
    assert len(j.history()) == 2
    assert j.history()[0]["type"] == "stage_start"


def test_terminal_flag():
    j = Job({})
    assert not j.is_terminal()
    j.status = "completed"
    assert j.is_terminal()


def test_subscriber_receives_event():
    async def go():
        j = Job({})
        q = j.subscribe()
        j.emit("hello")
        return await asyncio.wait_for(q.get(), timeout=1)

    ev = asyncio.run(go())
    assert ev["type"] == "hello"


def test_unsubscribe_stops_delivery():
    j = Job({})
    q = j.subscribe()
    j.unsubscribe(q)
    j.emit("x")
    assert q.empty()


def test_manager_create_get_remove():
    m = JobManager()
    job = m.create({"topic": "t"})
    assert m.get(job.id) is job
    m.remove(job.id)
    assert m.get(job.id) is None


def test_sse_format():
    out = sse({"type": "completed", "seq": 3})
    assert out.startswith("data: ") and out.endswith("\n\n")
    assert '"type": "completed"' in out


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
