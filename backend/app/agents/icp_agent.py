"""
ICP Agent — Ideal Customer Profile analysis.

Accepts a startup idea and returns a deeply tailored ICP breakdown
including target customer type, industries, buyer titles, pain points,
location hints, product category, search intent, and 5 specific
web-search queries designed to find real prospects.

Falls back to idea-aware mock data if OpenAI is unavailable.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.services.openai_service import call_openai_json

logger = logging.getLogger(__name__)

# ── Prompt template ──────────────────────────────────────────────

ICP_PROMPT = """\
Analyze this startup idea and return a specific Ideal Customer Profile.

Idea: {idea}

Rules:
- Every field must be tailored to THIS idea. No generic SaaS/marketing answers.
- target_customer_type = who BUYS this (e.g. "restaurant owners", "dental clinic managers").
- industries = the customers' industries, NOT the product's industry.
- search_queries = 5 Google queries to find target businesses' contact pages.
- location_hints = geography if mentioned, else ["Any / Global"].
- product_category = short label for the product (e.g. "AI scheduling tool").
- Be specific. Generic answers are WRONG.

Return ONLY JSON with this schema:
{{
  "summary":"2-3 sentence ICP summary",
  "target_customer_type":"single phrase",
  "ideal_customers":["segment1","segment2"],
  "industries":["industry1","industry2"],
  "buyer_titles":["title1","title2"],
  "pain_points":["pain1","pain2"],
  "value_proposition":"concise value prop",
  "product_category":"short label",
  "search_intent":"one sentence",
  "location_hints":["location or Any / Global"],
  "search_queries":["query1","query2","query3","query4","query5"],
  "qualification_criteria":["criterion1","criterion2"]
}}"""

# ── Required keys for validation ─────────────────────────────────

_REQUIRED_KEYS = {
    "summary",
    "target_customer_type",
    "ideal_customers",
    "industries",
    "buyer_titles",
    "pain_points",
    "value_proposition",
    "product_category",
    "search_intent",
    "location_hints",
    "search_queries",
    "qualification_criteria",
}

# ── Keyword-based industry / customer mapping for mock fallback ──

_IDEA_KEYWORD_MAP: List[Dict[str, Any]] = [
    {
        "keywords": ["restaurant", "restaurants", "cafe", "cafes", "diner",
                     "bistro", "food truck", "eatery", "dining"],
        "target_customer_type": "independent restaurant owners",
        "industries": ["Food & Beverage", "Restaurants", "Hospitality"],
        "ideal_customers": [
            "Independent restaurant owners",
            "Small restaurant chains (2-10 locations)",
            "Cafe and bistro operators",
        ],
        "buyer_titles": ["Owner", "General Manager", "Restaurant Manager"],
        "pain_points": [
            "No professional online presence",
            "Losing customers to competitors with online ordering",
            "Manual reservation management",
            "Difficulty attracting new local customers",
        ],
        "search_queries": [
            "independent restaurant contact us",
            "local restaurant owner website",
            "small restaurant business contact page",
            "family restaurant near me contact",
            "restaurant without online ordering",
        ],
    },
    {
        "keywords": ["dental", "dentist", "orthodontist", "clinic", "clinics",
                     "dental clinic"],
        "target_customer_type": "dental clinic owners and managers",
        "industries": ["Dental Care", "Healthcare", "Medical Practices"],
        "ideal_customers": [
            "Independent dental clinics",
            "Small dental practice groups",
            "Orthodontist offices",
        ],
        "buyer_titles": ["Dentist / Owner", "Practice Manager",
                         "Office Manager", "Clinic Director"],
        "pain_points": [
            "Missed calls and lost appointment bookings",
            "High no-show rates",
            "Manual appointment scheduling",
            "Difficulty managing patient follow-ups",
        ],
        "search_queries": [
            "dental clinic contact us appointment",
            "independent dentist office website",
            "dental practice contact page",
            "orthodontist clinic appointment booking",
            "small dental office owner",
        ],
    },
    {
        "keywords": ["grocery", "groceries", "supermarket", "food store",
                     "convenience store"],
        "target_customer_type": "small grocery store operators",
        "industries": ["Grocery Retail", "Food Retail",
                       "Convenience Stores"],
        "ideal_customers": [
            "Independent grocery store owners",
            "Small supermarket chains",
            "Specialty food shops",
        ],
        "buyer_titles": ["Store Owner", "Store Manager",
                         "Operations Manager"],
        "pain_points": [
            "Inventory waste and spoilage",
            "Inaccurate demand forecasting",
            "Manual stock counting",
            "Thin profit margins",
        ],
        "search_queries": [
            "independent grocery store contact",
            "small supermarket owner website",
            "local grocery store contact page",
            "specialty food store business",
            "neighborhood grocery store",
        ],
    },
    {
        "keywords": ["real estate", "realtor", "realtors", "property",
                     "brokerage", "housing", "homes"],
        "target_customer_type": "real estate agents and brokerages",
        "industries": ["Real Estate", "Property Management",
                       "Real Estate Brokerage"],
        "ideal_customers": [
            "Independent real estate agents",
            "Small real estate brokerages",
            "Property management firms",
        ],
        "buyer_titles": ["Real Estate Agent", "Broker", "Managing Broker",
                         "Agency Owner"],
        "pain_points": [
            "Slow lead response times",
            "Manual follow-up with buyers and sellers",
            "Difficulty managing multiple listings",
            "Client communication bottlenecks",
        ],
        "search_queries": [
            "real estate agent contact page",
            "independent realtor website",
            "small real estate brokerage contact",
            "property management company contact us",
            "local real estate agency",
        ],
    },
    {
        "keywords": ["gym", "gyms", "fitness", "workout", "personal training",
                     "yoga", "pilates", "crossfit"],
        "target_customer_type": "gym and fitness studio owners",
        "industries": ["Fitness & Wellness", "Health Clubs",
                       "Sports & Recreation"],
        "ideal_customers": [
            "Independent gym owners",
            "Boutique fitness studios",
            "Yoga and pilates studios",
            "CrossFit box owners",
        ],
        "buyer_titles": ["Owner", "Studio Manager", "Fitness Director",
                         "Head Coach"],
        "pain_points": [
            "Class scheduling and booking chaos",
            "Membership churn",
            "Manual attendance tracking",
            "No centralized booking system",
        ],
        "search_queries": [
            "local gym contact us page",
            "fitness studio owner website",
            "boutique gym booking classes",
            "yoga studio contact page",
            "independent gym membership",
        ],
    },
    {
        "keywords": ["school", "schools", "tutor", "tutoring", "education",
                     "homework", "learning center", "academy"],
        "target_customer_type": "tutoring centers and education providers",
        "industries": ["Education", "Tutoring Services",
                       "After-School Programs"],
        "ideal_customers": [
            "Independent tutoring centers",
            "After-school learning academies",
            "Online tutoring platforms",
            "Private education providers",
        ],
        "buyer_titles": ["Center Director", "Owner", "Head Tutor",
                         "Education Manager"],
        "pain_points": [
            "Tracking student progress manually",
            "Scheduling conflicts between tutors and students",
            "Parent communication gaps",
            "Homework tracking is inconsistent",
        ],
        "search_queries": [
            "tutoring center contact us",
            "local learning center website",
            "after school program contact page",
            "private tutoring service owner",
            "education academy near me",
        ],
    },
    {
        "keywords": ["ecommerce", "e-commerce", "online store", "shopify",
                     "woocommerce", "online shop", "dropshipping"],
        "target_customer_type": "e-commerce store owners",
        "industries": ["E-Commerce", "Online Retail",
                       "Direct-to-Consumer Brands"],
        "ideal_customers": [
            "Small Shopify / WooCommerce store owners",
            "DTC brands scaling past $1M revenue",
            "Niche e-commerce retailers",
        ],
        "buyer_titles": ["Founder", "E-Commerce Manager",
                         "Head of Digital", "Marketing Director"],
        "pain_points": [
            "Cart abandonment rates too high",
            "Customer acquisition costs rising",
            "Inventory syncing across channels",
            "Poor post-purchase experience",
        ],
        "search_queries": [
            "small ecommerce store contact us",
            "independent online store owner",
            "shopify store contact page",
            "DTC brand founder website",
            "online retail business contact",
        ],
    },
    {
        "keywords": ["healthcare", "health", "medical", "patient", "hospital",
                     "physician", "doctor", "telehealth"],
        "target_customer_type": "healthcare providers and clinics",
        "industries": ["Healthcare", "Medical Practices", "Telehealth"],
        "ideal_customers": [
            "Independent medical practices",
            "Small clinics and urgent care centers",
            "Telehealth providers",
        ],
        "buyer_titles": ["Practice Owner", "Clinic Manager",
                         "Medical Director", "Office Administrator"],
        "pain_points": [
            "Patient scheduling inefficiencies",
            "Administrative overhead eating into care time",
            "Poor patient engagement between visits",
            "Compliance and record-keeping burden",
        ],
        "search_queries": [
            "medical practice contact page",
            "independent clinic website",
            "small healthcare provider contact us",
            "urgent care center owner",
            "physician practice management",
        ],
    },
]


def _match_idea_keywords(idea: str) -> Optional[Dict[str, Any]]:
    """Find the best keyword-map entry matching the idea."""
    idea_lower = idea.lower()
    best_match = None
    best_count = 0
    for entry in _IDEA_KEYWORD_MAP:
        hits = sum(1 for kw in entry["keywords"] if kw in idea_lower)
        if hits > best_count:
            best_count = hits
            best_match = entry
    return best_match if best_count > 0 else None


def _build_mock(idea: str) -> Dict[str, Any]:
    """Return idea-aware mock data — NOT generic SaaS boilerplate."""
    short = idea[:80].rstrip()
    match = _match_idea_keywords(idea)

    if match:
        return {
            "summary": (
                f'Based on the idea "{short}…", the ideal customers are '
                f'{match["target_customer_type"]} looking to improve '
                f"operations and grow their business."
            ),
            "target_customer_type": match["target_customer_type"],
            "ideal_customers": match["ideal_customers"],
            "industries": match["industries"],
            "buyer_titles": match["buyer_titles"],
            "pain_points": match["pain_points"],
            "value_proposition": (
                f"Help {match['target_customer_type']} solve their biggest "
                f"operational challenges with a purpose-built solution."
            ),
            "product_category": "business tool",
            "search_intent": (
                f"Find real {match['target_customer_type']} who could "
                f"benefit from this product."
            ),
            "location_hints": ["Any / Global"],
            "search_queries": match["search_queries"],
            "qualification_criteria": [
                f"Business is in: {', '.join(match['industries'][:2])}",
                "Has a public website or contact page",
                "Appears to be independently owned or a small chain",
            ],
        }

    # Ultimate generic fallback (only when no keyword matches at all)
    target_kw = _extract_target_phrase(idea)
    return {
        "summary": (
            f'Based on the idea "{short}…", the ideal customers are '
            f"small-to-mid-size businesses in the {target_kw} space."
        ),
        "target_customer_type": f"{target_kw} businesses",
        "ideal_customers": [
            f"Small {target_kw} companies",
            f"Mid-market {target_kw} operators",
            f"Independent {target_kw} providers",
        ],
        "industries": [target_kw.title(), "Small Business", "Local Services"],
        "buyer_titles": ["Owner", "Manager", "Director of Operations"],
        "pain_points": [
            "Manual processes slowing growth",
            "Difficulty reaching new customers",
            "Lack of modern tooling",
            "Operational inefficiencies",
        ],
        "value_proposition": (
            f"A modern solution to help {target_kw} businesses operate "
            "more efficiently."
        ),
        "product_category": "business tool",
        "search_intent": f"Find {target_kw} businesses with contact pages.",
        "location_hints": ["Any / Global"],
        "search_queries": [
            f"{target_kw} business contact us",
            f"{target_kw} company website",
            f"small {target_kw} owner contact page",
            f"independent {target_kw} provider",
            f"local {target_kw} service contact",
        ],
        "qualification_criteria": [
            "Has a public website",
            f"Operates in the {target_kw} space",
            "Small-to-mid-size operation",
        ],
    }


def _extract_target_phrase(idea: str) -> str:
    """Pull the most meaningful 2-3 word phrase from the idea."""
    _STOP = {
        "a", "an", "the", "for", "and", "or", "but", "in", "on", "at",
        "to", "of", "is", "are", "that", "this", "with", "from", "by",
        "tool", "platform", "software", "system", "app", "application",
        "startup", "solution", "product", "service", "website", "site",
        "ai", "ml", "smart", "automated", "powered", "using", "uses",
        "helps", "automates", "built", "build", "creates", "it",
        "saas", "b2b", "b2c", "tech", "digital", "online", "cloud",
        "new", "modern", "advanced", "next", "gen", "generation",
    }
    words = re.findall(r"[a-zA-Z]+", idea.lower())
    meaningful = [w for w in words if w not in _STOP and len(w) > 2]
    return " ".join(meaningful[:3]) if meaningful else "business"


# ── Main entry point ─────────────────────────────────────────────

async def analyze_icp(idea: str) -> Dict[str, Any]:
    """
    Analyse a startup idea and return an Ideal Customer Profile.

    Calls OpenAI with a structured prompt.  If the API call or JSON
    parsing fails, returns idea-aware mock data so the frontend always
    gets a usable, relevant response.
    """
    logger.info("=" * 60)
    logger.info("ICP AGENT — idea: %s", idea[:120])

    prompt = ICP_PROMPT.format(idea=idea)

    try:
        result = await call_openai_json(prompt, temperature=0.6, max_tokens=800)

        missing = _REQUIRED_KEYS - set(result.keys())
        if missing:
            logger.warning(
                "OpenAI response missing keys %s — falling back to mock",
                missing,
            )
            return _build_mock(idea)

        logger.info(
            "ICP extracted — target: %s | industries: %s",
            result.get("target_customer_type", "?"),
            result.get("industries", []),
        )
        return result

    except (RuntimeError, ValueError) as exc:
        logger.warning("ICP agent falling back to mock data: %s", exc)
        return _build_mock(idea)

    except Exception as exc:
        logger.error("Unexpected ICP agent error: %s", exc)
        return _build_mock(idea)
