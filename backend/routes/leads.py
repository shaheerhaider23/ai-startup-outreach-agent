"""
Leads routes — endpoints for managing startup leads.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Lead(BaseModel):
    """A single startup lead."""
    id: int
    name: str
    industry: str
    website: str = ""
    contact_email: str = ""


# In-memory placeholder — replace with a real DB later
_leads: list[dict] = [
    {"id": 1, "name": "NovaTech", "industry": "AI/ML", "website": "https://novatech.example.com", "contact_email": "hello@novatech.example.com"},
    {"id": 2, "name": "GreenPulse", "industry": "CleanTech", "website": "https://greenpulse.example.com", "contact_email": "info@greenpulse.example.com"},
]


@router.get("/", response_model=list[Lead])
async def list_leads():
    """Return all stored leads."""
    return _leads


@router.post("/", response_model=Lead)
async def add_lead(lead: Lead):
    """Add a new lead."""
    _leads.append(lead.model_dump())
    return lead
