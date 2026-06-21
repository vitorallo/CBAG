"""CBAG LLM refinement (stage 2).

Rewrites raw buzzword text into a coherent, confident, on-topic corporate
monologue in a chosen persona — while preserving the comedic emptiness. Talks
to a local Ollama (the host's existing instance by default) via its /api/chat
endpoint. No external network calls.

Prompt assembly (`build_messages`) is pure and import-light so it can be unit
tested without httpx or a running model.
"""
from ..config import settings

# Persona key -> system-prompt voice. Unknown personas fall back to the default.
PERSONAS = {
    "visionary-ceo": (
        "You are a visionary tech CEO delivering an inspiring keynote — grandiose, "
        "confident, sweeping vision."
    ),
    "mckinsey-consultant": (
        "You are a McKinsey management consultant — crisp frameworks, hedged "
        "certainty, strategic jargon."
    ),
    "startup-founder": (
        "You are a hyped startup founder pitching investors — disruptive, urgent, "
        "hockey-stick optimism."
    ),
    "thought-leader": (
        "You are a LinkedIn thought leader — humble-brag anecdotes and "
        "profound-sounding platitudes."
    ),
}
DEFAULT_PERSONA = "visionary-ceo"

LENGTH_GUIDE = {
    "short": "exactly ONE short, punchy sentence (about 12-18 words)",
    "medium": "2-3 sentences",
    "long": "one short paragraph (4-6 sentences)",
}
DEFAULT_LENGTH = "medium"

SYSTEM_BASE = (
    "You rewrite corporate buzzword nonsense into a smooth, confident, on-topic "
    "monologue. Keep it grand and persuasive but DELIBERATELY empty of real "
    "substance — it must SOUND insightful while saying nothing concrete. VARY your "
    "vocabulary: do not repeat the same buzzword or lean on one adjective. Output "
    "only the monologue, with no preamble, disclaimers, or self-commentary."
)


def build_messages(raw_text, topic=None, persona=None, length=None):
    """Assemble chat messages plus the resolved persona/length keys (pure)."""
    persona_key = persona if persona in PERSONAS else DEFAULT_PERSONA
    length_key = length if length in LENGTH_GUIDE else DEFAULT_LENGTH
    system = (
        f"{SYSTEM_BASE}\n\nPersona: {PERSONAS[persona_key]}\n"
        f"Target length: {LENGTH_GUIDE[length_key]}."
    )
    user = (
        f"Topic: {topic or 'corporate strategy'}\n\n"
        f"Raw material to transform:\n{raw_text}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return messages, persona_key, length_key


async def refine(raw_text, topic=None, persona=None, length=None, timeout=90.0):
    """Refine raw BS via the local Ollama. Raises on failure (bounded by timeout)."""
    import httpx  # imported lazily so unit tests of build_messages need no deps

    messages, persona_key, length_key = build_messages(raw_text, topic, persona, length)
    payload = {"model": settings.llm_model, "messages": messages, "stream": False}
    url = f"{settings.llm_base_url}/api/chat"

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return {
        "text": data["message"]["content"].strip(),
        "persona": persona_key,
        "length": length_key,
        "model": settings.llm_model,
    }
