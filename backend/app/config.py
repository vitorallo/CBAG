"""Environment-driven configuration for the CBAG backend.

Every value has a documented default so the stack runs out of the box, and any
of them can be overridden via environment variables (see .env.example).
"""
import os


class Settings:
    # Backend
    backend_port: int = int(os.environ.get("BACKEND_PORT", "8000"))

    # Model service base URLs (compose DNS names by default; override for LAN/GB10 IP)
    llm_base_url: str = os.environ.get("LLM_BASE_URL", "http://llm:11434")
    # Ollama model used for refinement (must be pulled in that Ollama). Default is a
    # small, fast, Apache-2.0 instruct model so the demo is quick on a fresh box; the
    # LLM only drives stage-2 text refinement (voice/video are separate). Override
    # with CBAG_LLM_MODEL (e.g. gpt-oss:20b for richer prose).
    llm_model: str = os.environ.get("CBAG_LLM_MODEL", "qwen2.5:3b")
    tts_base_url: str = os.environ.get("TTS_BASE_URL", "http://tts:8100")
    video_base_url: str = os.environ.get("VIDEO_BASE_URL", "http://video:8200")

    # Shared artifact storage (mounted into services by docker-compose)
    artifact_root: str = os.environ.get("ARTIFACT_ROOT", "/artifacts")
    # Job artifact retention (seconds) before the sweeper removes them.
    artifact_ttl_seconds: int = int(os.environ.get("ARTIFACT_TTL_SECONDS", "86400"))


settings = Settings()
