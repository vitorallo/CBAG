"""Unit tests for LLM refinement prompt assembly (no network / no httpx).

Runnable standalone or via pytest:
    python3 backend/tests/test_refine.py
    pytest backend/tests/test_refine.py
"""
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.pipeline import refine  # noqa: E402


def test_unknown_persona_falls_back():
    _, persona_key, _ = refine.build_messages("raw", "topic", "does-not-exist", "medium")
    assert persona_key == refine.DEFAULT_PERSONA


def test_known_persona_used():
    _, persona_key, _ = refine.build_messages("raw", "topic", "mckinsey-consultant", "short")
    assert persona_key == "mckinsey-consultant"


def test_unknown_length_falls_back():
    _, _, length_key = refine.build_messages("raw", "topic", "visionary-ceo", "enormous")
    assert length_key == refine.DEFAULT_LENGTH


def test_messages_include_raw_and_topic():
    messages, _, _ = refine.build_messages("RAWBS123", "Quantum Synergy", "startup-founder", "long")
    blob = " ".join(m["content"] for m in messages)
    assert "RAWBS123" in blob
    assert "Quantum Synergy" in blob


def test_persona_voice_in_system_prompt():
    messages, _, _ = refine.build_messages("raw", "t", "thought-leader", "short")
    system = messages[0]["content"]
    assert "LinkedIn thought leader" in system


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run())
