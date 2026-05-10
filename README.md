# AI Startup Outreach Agent System

An AI-powered system for researching startups and generating personalised outreach messages. Built with **FastAPI** (backend) and **Next.js** (frontend).

---

## 📁 Project Structure

```
project/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment variable template
│   ├── routes/
│   │   ├── outreach.py          # Outreach generation endpoints
│   │   └── leads.py             # Lead management endpoints
│   ├── agents/
│   │   ├── outreach_agent.py    # LLM-powered outreach message agent
│   │   └── research_agent.py    # Startup research agent
│   ├── services/
│   │   ├── llm_service.py       # OpenAI / LLM wrapper
│   │   └── email_service.py     # Email sending service
│   └── data/
│       └── sample_leads.json    # Seed data for development
│
├── frontend/
│   ├── package.json             # Node.js dependencies
│   ├── next.config.js           # Next.js configuration (API proxy)
│   ├── tsconfig.json            # TypeScript configuration
│   └── src/
│       ├── app/
│       │   ├── layout.tsx       # Root layout
│       │   ├── globals.css      # Global styles & design tokens
│       │   └── page.tsx         # Home page
│       ├── components/
│       │   ├── Header.tsx       # Site header
│       │   └── LeadCard.tsx     # Startup lead card
│       └── lib/
│           └── api.ts           # Typed API fetch helpers
│
└── README.md
```

---

## 🚀 How to Run

### 1. Backend (FastAPI)

```bash
# Navigate to the backend folder
cd project/backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start the server
uvicorn main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**.  
Interactive docs at **http://localhost:8000/docs**.

---

### 2. Frontend (Next.js)

```bash
# Navigate to the frontend folder
cd project/frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:3000**.  
API calls from the frontend are proxied to the backend via `next.config.js`.

---

## 🔌 API Endpoints (Backend)

| Method | Path                   | Description                       |
| ------ | ---------------------- | --------------------------------- |
| GET    | `/`                    | Health check message              |
| GET    | `/health`              | Health status                     |
| GET    | `/api/leads/`          | List all startup leads            |
| POST   | `/api/leads/`          | Add a new lead                    |
| POST   | `/api/outreach/generate` | Generate an outreach message    |

---

## 🛠 Next Steps

- [ ] Wire `OutreachAgent` to the OpenAI API via `LLMService`
- [ ] Implement `ResearchAgent` with web search / scraping
- [ ] Connect `EmailService` to a real email provider (SendGrid, Resend, etc.)
- [ ] Replace in-memory lead storage with a database (SQLite / PostgreSQL)
- [ ] Add authentication and rate limiting
- [ ] Build out the frontend dashboard with real API integration
