"""
Outreach Agent — generates personalised outreach messages using an LLM.
"""


class OutreachAgent:
    """Agent responsible for crafting outreach emails and messages."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    async def generate_message(
        self,
        startup_name: str,
        industry: str,
        target_contact: str,
        context: str = "",
    ) -> dict:
        """
        Generate a personalised outreach message.

        Returns:
            dict with keys: subject, message, tone
        """
        # TODO: integrate OpenAI / LLM call here
        return {
            "subject": f"Quick intro — {startup_name}",
            "message": f"Hi {target_contact}, I'd love to connect about {startup_name} in the {industry} space.",
            "tone": "professional",
        }
