"""
Application configuration — loads environment variables from .env
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend root (one level above app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


class Settings:
    """Centralised, read-only access to environment variables."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

    def __init__(self) -> None:
        if not self.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Add it to backend/.env and restart the server."
            )


# Singleton instance — import this wherever config is needed
settings = Settings()
