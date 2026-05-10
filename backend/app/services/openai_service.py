"""
OpenAI service — initialises the client and exposes helper functions.
The API key is loaded from app.config and never exposed to the frontend.
"""

import json
import logging
from typing import Any, Dict, Optional

from openai import APIConnectionError, APIStatusError, OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    """Create OpenAI client lazily so missing keys don't crash on import."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to backend/.env or Streamlit secrets."
        )
    return OpenAI(api_key=api_key)


async def call_openai_json(
    prompt: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """
    Send *prompt* to OpenAI and return the response parsed as JSON.

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
    chosen_model = model or settings.OPENAI_MODEL

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
        logger.error("OpenAI connection error: %s", exc)
        raise RuntimeError(
            "Could not connect to OpenAI. Check your network."
        ) from exc
    except APIStatusError as exc:
        logger.error(
            "OpenAI API error %s: %s", exc.status_code, exc.message
        )
        raise RuntimeError(
            f"OpenAI API error ({exc.status_code}): {exc.message}"
        ) from exc

    raw_text = response.choices[0].message.content or ""

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from OpenAI: %s", raw_text[:200])
        raise ValueError(
            "OpenAI returned a response that is not valid JSON."
        ) from exc
