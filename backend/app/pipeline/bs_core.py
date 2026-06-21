"""CBAG BS core — deterministic corporate-buzzword text generation.

Pure CPU, no dependencies. Fills the templates in grammar.py to produce raw
buzzword sentences with controllable length, buzzword density, optional topic
seeding, and an optional deterministic seed for reproducibility.
"""
import random
import re

from . import grammar

_SLOT = re.compile(r"\{([VN])\}")
_MAX_ADJ = 3  # cap stacked adjectives so density=1.0 still terminates


def _noun_phrase(rng, density, topic_seeds, force_topic=False):
    """Build a noun phrase, optionally topical, with density-driven adjectives."""
    if force_topic and topic_seeds:
        head = rng.choice(topic_seeds)
    elif topic_seeds and rng.random() < 0.35:
        head = rng.choice(topic_seeds)
    else:
        head = rng.choice(grammar.NOUNS)

    parts = [head]
    used_adj = set()
    while len(used_adj) < _MAX_ADJ and rng.random() < density:
        adj = rng.choice(grammar.ADJECTIVES)
        if adj in used_adj:
            break  # avoid repeating an adjective in the same phrase
        used_adj.add(adj)
        parts.insert(0, adj)
    return " ".join(parts)


def _make_sentence(rng, density, topic_seeds, force_topic):
    template = rng.choice(grammar.TEMPLATES)
    topic_used = [False]

    def repl(match):
        if match.group(1) == "V":
            return rng.choice(grammar.VERBS)
        ft = force_topic and not topic_used[0]
        phrase = _noun_phrase(rng, density, topic_seeds, force_topic=ft)
        if ft:
            topic_used[0] = True
        return phrase

    sentence = _SLOT.sub(repl, template)
    return sentence[0].upper() + sentence[1:]


def generate(length=3, density=0.5, topic_seeds=None, seed=None):
    """Generate raw corporate-buzzword text.

    Args:
        length: number of sentences (>= 1).
        density: 0.0-1.0 probability of stacking buzzword adjectives.
        topic_seeds: optional list of words to bias the output toward a topic.
        seed: optional int for deterministic, reproducible output.

    Returns:
        A string of `length` buzzword sentences. When topic_seeds are given, at
        least the first sentence is guaranteed to include a topic word.
    """
    rng = random.Random(seed)
    density = max(0.0, min(1.0, float(density)))
    length = max(1, int(length))
    topic_seeds = [t.strip() for t in (topic_seeds or []) if t and t.strip()]

    sentences = []
    for i in range(length):
        force_topic = bool(topic_seeds) and i == 0
        sentences.append(_make_sentence(rng, density, topic_seeds, force_topic))
    return " ".join(sentences)
