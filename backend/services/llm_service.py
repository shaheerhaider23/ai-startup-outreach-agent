"""
LLM Service — centralised wrapper around the language model provider.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """Thin wrapper around the OpenAI API (or any LLM provider)."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            print("⚠️  OPENAI_API_KEY is not set — LLM calls will fail.")

    async def chat(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
        """
        Send a chat completion request and return the assistant's reply.
        """
        # TODO: implement actual OpenAI call
        return f"[LLM placeholder response to: {user_prompt[:60]}...]"
