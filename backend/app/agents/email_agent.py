"""
Outreach Email Agent — Generates formal, professional B2B outreach emails.
"""

import json
import logging
from typing import Any, Dict

from app.services.openai_service import call_openai_json

logger = logging.getLogger(__name__)

# ── Token-optimised prompt (formal tone enforced) ────────────────

EMAIL_PROMPT = """\
Write a formal B2B outreach email for this startup idea targeting the lead.

Idea: {idea}
Lead: {lead_json}

Strict rules:
- Formal, professional, business-appropriate tone throughout.
- 100-160 words. No filler.
- Structure: Greeting → Context → Value prop → CTA → Closing → Opt-out.
- Greeting: "Dear [company] Team," (do NOT invent personal names).
- Mention the company name once naturally in the opening.
- Value proposition: use cautious language ("may help", "could support",
  "designed to help", "aims to reduce"). Do NOT promise guaranteed results.
- CTA: ask for a brief introductory call or permission to share more info.
- Closing: "Best regards," followed by a sender placeholder.
- Include a polite opt-out line as compliance_footer.
- No slang, hype, emojis, exclamation marks, or aggressive sales language.
- Do NOT use "Hey", "Hi there", or overly casual greetings.
- Return ONLY compact JSON, no markdown.

JSON schema:
{{"subject":"","email_body":"","cta":"","personalization_reason":"","compliance_footer":""}}
"""


def _slim_lead(lead: Dict[str, Any]) -> str:
    """Send only the fields needed for email generation to save tokens."""
    slim = {
        "company": lead.get("company_name", ""),
        "industry": lead.get("industry", ""),
        "pain_point": lead.get("pain_point", ""),
        "website": lead.get("website", ""),
        "why_fit": lead.get("why_fit", ""),
        "evidence": lead.get("evidence", ""),
    }
    # Strip empty values to save tokens
    slim = {k: v for k, v in slim.items() if v}
    return json.dumps(slim, separators=(",", ":"))


def _build_mock(idea: str, lead: Dict[str, Any]) -> Dict[str, Any]:
    """Formal fallback email when OpenAI is unavailable."""
    company = lead.get("company_name", "your organisation")
    industry = lead.get("industry", "your industry")
    pain_point = lead.get("pain_point", "operational challenges")
    short_idea = idea[:60].rstrip()

    return {
        "subject": f"Introduction — a solution that may support {company}",
        "email_body": (
            f"Dear {company} Team,\n\n"
            f"I am reaching out because I noticed that {company} operates "
            f"in the {industry} space, where many organisations face "
            f"{pain_point}.\n\n"
            f"We are developing a solution ({short_idea}) that is designed "
            f"to help businesses like yours address this challenge more "
            f"efficiently.\n\n"
            f"Would it be possible to schedule a brief introductory call "
            f"to explore whether this could be relevant to your team?\n\n"
            f"Best regards,\n"
            f"[Your Name]\n"
            f"Founder"
        ),
        "cta": (
            "Would it be possible to schedule a brief introductory call "
            "to explore whether this could be relevant to your team?"
        ),
        "personalization_reason": (
            f"Targeting {company} because they operate in {industry} "
            f"and may experience {pain_point}."
        ),
        "compliance_footer": (
            "If you would prefer not to receive further communication, "
            "please reply and let me know. I will remove you from my list immediately."
        ),
    }


async def generate_email_draft(
    idea: str,
    lead: Dict[str, Any],
    tone: str = "professional",
) -> Dict[str, Any]:
    """
    Generate a formal outreach email draft.

    Uses OpenAI to create the email. Falls back to a formal template
    if the API is unavailable.
    """
    prompt = EMAIL_PROMPT.format(
        idea=idea,
        lead_json=_slim_lead(lead),
    )

    try:
        result = await call_openai_json(prompt, temperature=0.5, max_tokens=600)

        required_keys = {
            "subject",
            "email_body",
            "cta",
            "personalization_reason",
            "compliance_footer",
        }
        missing = required_keys - set(result.keys())
        if missing:
            logger.warning(
                "OpenAI response missing keys %s — falling back to mock",
                missing,
            )
            return _build_mock(idea, lead)

        return result

    except (RuntimeError, ValueError) as exc:
        logger.warning("Email agent falling back to mock data: %s", exc)
        return _build_mock(idea, lead)

    except Exception as exc:
        logger.error("Unexpected email agent error: %s", exc)
        return _build_mock(idea, lead)
