"""CBAG default-voice catalog and resolution (pure, import-light for testing).

Maps friendly names ("male"/"female") to Kokoro voice ids. An unrecognized name
is passed through as a raw Kokoro voice id, so advanced users can request any of
Kokoro's built-in voices directly.
"""

# Pre-baked default voices (1 male, 1 female, US English).
DEFAULT_VOICES = {
    "female": "af_heart",
    "male": "am_michael",
}


def resolve_voice(name):
    if not name:
        return DEFAULT_VOICES["female"]
    return DEFAULT_VOICES.get(name.lower(), name)
