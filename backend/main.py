"""
AI Startup Outreach Agent System - Backend Entry Point
FastAPI application serving the outreach agent APIs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.outreach import router as outreach_router
from routes.leads import router as leads_router

app = FastAPI(
    title="AI Startup Outreach Agent",
    description="Backend API for the AI-powered startup outreach system",
    version="0.1.0",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(outreach_router, prefix="/api/outreach", tags=["Outreach"])
app.include_router(leads_router, prefix="/api/leads", tags=["Leads"])


@app.get("/")
async def root():
    return {"message": "AI Startup Outreach Agent API is running 🚀"}


@app.get("/health")
async def health():
    return {"status": "ok"}
