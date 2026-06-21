"""Unit tests for default-voice resolution (pure, no model/deps).

    python3 services/tts/test_voices.py
    pytest services/tts/test_voices.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from voices import DEFAULT_VOICES, resolve_voice  # noqa: E402


def test_female_and_male_map():
    assert resolve_voice("female") == DEFAULT_VOICES["female"]
    assert resolve_voice("male") == DEFAULT_VOICES["male"]


def test_case_insensitive():
    assert resolve_voice("MALE") == DEFAULT_VOICES["male"]


def test_empty_defaults_to_female():
    assert resolve_voice("") == DEFAULT_VOICES["female"]
    assert resolve_voice(None) == DEFAULT_VOICES["female"]


def test_raw_voice_passthrough():
    # advanced: an unknown name is treated as a raw Kokoro voice id
    assert resolve_voice("bf_emma") == "bf_emma"


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
