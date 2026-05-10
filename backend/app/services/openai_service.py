"""
Groq service — initialises the Groq client and exposes helper functions.
The API key is loaded from app.config and never exposed to the frontend.

Groq's API is OpenAI-compatible, so we use the OpenAI client pointed at
Groq's base URL for simplicity.
"""

import json
import logging
from typing import Any, Dict, Optional

from groq import APIConnectionError, APIStatusError, Groq

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Groq:
    """Create Groq client lazily so missing keys don't crash on import."""
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env or Streamlit secrets."
        )
    return Groq(api_key=api_key)


async def call_openai_json(
    prompt: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """
    Send *prompt* to Groq and return the response parsed as JSON.

    Parameters
    ----------
    prompt : str
        The user/system prompt to send.
    model : str, optional
        Override the default model from config.
    temperature : float
        Sampling temperature (0–2).
    max_tokens : int
        Max tokens in the completion.

    Returns
    -------
    dict
        Parsed JSON from the model's response.

    Raises
    ------
    ValueError
        If the model's response is not valid JSON.
    RuntimeError
        If the API call fails (network, auth, rate-limit, etc.).
    """
    chosen_model = model or settings.GROQ_MODEL

    try:
        response = _get_client().chat.completions.create(
            model=chosen_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. "
                        "Always respond with valid JSON and nothing else."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except APIConnectionError as exc:
        logger.error("Groq connection error: %s", exc)
        raise RuntimeError(
            "Could not connect to Groq. Check your network."
        ) from exc
    except APIStatusError as exc:
        logger.error(
            "Groq API error %s: %s", exc.status_code, exc.message
        )
        raise RuntimeError(
            f"Groq API error ({exc.status_code}): {exc.message}"
        ) from exc

    raw_text = response.choices[0].message.content or ""

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from Groq: %s", raw_text[:200])
        raise ValueError(
            "Groq returned a response that is not valid JSON."
        ) from exc
