"""
Application configuration — loads environment variables.

Priority order:
  1. Streamlit secrets (st.secrets) — used on Streamlit Community Cloud
  2. backend/.env file — used for local development
  3. Environment variables — fallback
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend root (one level above app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then env vars."""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


class Settings:
    """Centralised, read-only access to environment variables."""

    @property
    def GROQ_API_KEY(self) -> str:
        return _get_secret("GROQ_API_KEY", "")

    @property
    def GROQ_MODEL(self) -> str:
        return _get_secret("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def RESEND_API_KEY(self) -> str:
        return _get_secret("RESEND_API_KEY", "")


# Singleton instance — import this wherever config is needed
settings = Settings()
