"""Tests for the CBAG BS core generator.

Dependency-light: imports the pure-Python generator directly so it runs on the
dev box and inside the backend container alike. Runnable two ways:
    python3 backend/tests/test_bs_core.py     # standalone
    pytest backend/tests/test_bs_core.py      # via pytest
"""
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.pipeline import bs_core  # noqa: E402


def _sentences(text):
    return [s for s in text.split(".") if s.strip()]


def test_nonempty_default():
    text = bs_core.generate()
    assert text.strip()
    assert text.rstrip().endswith(".")
    assert len(text.split()) > 3


def test_length_honored():
    for n in (1, 3, 7, 12):
        assert len(_sentences(bs_core.generate(length=n, seed=1))) == n


def test_min_length_floor():
    # length < 1 is clamped up to 1 sentence
    assert len(_sentences(bs_core.generate(length=0))) == 1


def test_density_increases_words():
    low = bs_core.generate(length=8, density=0.0, seed=42)
    high = bs_core.generate(length=8, density=1.0, seed=42)
    assert len(high.split()) > len(low.split())


def test_seed_reproducible():
    a = bs_core.generate(length=5, density=0.6, topic_seeds=["fintech"], seed=7)
    b = bs_core.generate(length=5, density=0.6, topic_seeds=["fintech"], seed=7)
    assert a == b


def test_different_seeds_differ():
    a = bs_core.generate(length=5, seed=1)
    b = bs_core.generate(length=5, seed=2)
    assert a != b


def test_topic_seed_present():
    topics = ["blockchain", "fintech"]
    text = bs_core.generate(length=4, topic_seeds=topics, seed=3)
    assert any(t in text for t in topics)


def test_density_bounds_do_not_crash():
    # out-of-range density is clamped, not an error
    assert bs_core.generate(density=5.0, seed=1).strip()
    assert bs_core.generate(density=-1.0, seed=1).strip()


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
