"""
Outreach routes — endpoints for generating and sending outreach messages.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class OutreachRequest(BaseModel):
    """Request body for generating an outreach message."""
    startup_name: str
    industry: str
    target_contact: str
    context: str = ""


class OutreachResponse(BaseModel):
    """Response body with the generated outreach message."""
    message: str
    subject: str
    tone: str


@router.post("/generate", response_model=OutreachResponse)
async def generate_outreach(request: OutreachRequest):
    """Generate a personalised outreach message for a startup."""
    # TODO: wire up the outreach agent
    return OutreachResponse(
        message=f"Hi {request.target_contact}, I'd love to connect about {request.startup_name}.",
        subject=f"Quick intro — {request.startup_name}",
        tone="professional",
    )
