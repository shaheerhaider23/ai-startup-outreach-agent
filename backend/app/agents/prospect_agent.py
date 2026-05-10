"""
Prospect Research Agent — generates accurate, evidence-based prospect leads
that dynamically adapt to every startup idea.

Pipeline:
  1. Read the startup idea + ICP (including target_customer_type, industries,
     search_intent, search_queries, location_hints).
  2. Generate 5 targeted web-search queries — never hardcoded.
  3. Search the web via DuckDuckGo across all queries.
  4. Deduplicate results by normalised domain.
  5. Filter out irrelevant results (blogs, job boards, Wikipedia …).
  6. Score remaining results for ICP relevance.
  7. Format top results into structured leads via OpenAI (strict rules).
  8. Fall back to idea-specific demo leads if anything fails.

STRICT RULE — enforced at every stage:
  Never return generic SaaS / software / digital-marketing leads unless
  the user's startup idea specifically targets those companies.
"""

import json as _json
import logging
import random
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.services.openai_service import call_openai_json

logger = logging.getLogger(__name__)

# ── Optional DuckDuckGo import (handles package rename) ─────────
try:
    from ddgs import DDGS
    _DDG_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDG_AVAILABLE = True
    except ImportError:
        _DDG_AVAILABLE = False
        logger.warning("ddgs/duckduckgo-search not installed — web search disabled")

# ── Blocklists for relevance filtering ───────────────────────────

BLOCKED_DOMAINS = {
    # Social media
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "pinterest.com", "snapchat.com", "linkedin.com",
    # Reference / encyclopedias
    "wikipedia.org", "wikihow.com", "britannica.com",
    # Job boards
    "indeed.com", "glassdoor.com", "ziprecruiter.com", "monster.com",
    # Major news outlets
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnn.com", "foxnews.com",
    "reuters.com", "apnews.com", "theguardian.com", "washingtonpost.com",
    # Blogging / Q&A / forums
    "medium.com", "quora.com", "reddit.com", "stackoverflow.com",
    "tumblr.com", "substack.com",
    # Video
    "youtube.com", "vimeo.com",
    # Software directories / review sites
    "crunchbase.com", "g2.com", "capterra.com", "trustpilot.com",
    "producthunt.com", "alternativeto.net",
    # Government / generic
    "gov", "edu",
}

BLOCKED_PATH_KEYWORDS = [
    "/blog", "/article", "/news/", "/press-release",
    "/careers", "/jobs/", "/job/", "/hiring",
    "/wiki/", "/post/", "/tag/", "/category/",
]

LISTICLE_RE = re.compile(
    r"\b(top\s?\d+|best\s?\d+|\d+\s+best|list\s+of|vs\.?|versus"
    r"|review|ranking|comparison|alternatives)\b",
    re.IGNORECASE,
)

# ── Product-descriptor words (stripped when extracting target keywords) ──

_PRODUCT_WORDS = {
    "a", "an", "the", "for", "and", "or", "but", "in", "on", "at",
    "to", "of", "is", "are", "that", "this", "with", "from", "by",
    "tool", "platform", "software", "system", "app", "application",
    "startup", "solution", "product", "service", "website", "site",
    "ai", "ml", "machine", "learning", "automated", "smart",
    "intelligent", "powered", "based", "driven", "using", "uses",
    "helps", "automates", "provides", "built", "build", "creates",
    "saas", "b2b", "b2c", "tech", "digital", "online", "cloud",
    "new", "modern", "advanced", "next", "gen", "generation", "it",
}

# ── Fallback business-name prefixes ─────────────────────────────

_DEMO_PREFIXES = [
    "Premier", "City Center", "Coastal", "Valley", "Metro",
    "Heritage", "Summit", "Pacific", "Golden", "Capital",
    "Lakeside", "Sunrise", "Evergreen", "Bright", "Harmony",
]

# ═══════════════════════════════════════════════════════════════════
# OPENAI FORMATTING PROMPT  (token-optimized — no full ICP dump)
# ═══════════════════════════════════════════════════════════════════

PROSPECT_PROMPT = """\
Format these web search results into prospect leads.

Idea: {idea}
Target: {target_customer_type}
Industries: {target_industries}
Pain points: {pain_points}

Rules:
- Use ONLY provided results. Do NOT invent names, URLs, or locations.
- Every lead MUST have the exact URL from results as website and source_url.
- Do NOT create a lead if there is no URL.
- Exclude results that are not real potential customers for this idea.
- No generic SaaS/software leads unless the idea targets them.
- Return fewer leads rather than fake ones. Max {max_leads}.
- lead_score 50-98 based on industry match, evidence quality, contact page.
- Return ONLY compact JSON, no markdown.

Results:
{search_results}

JSON schema:
{{"leads":[{{"company_name":"","website":"","location":"","industry":"","contact_hint":"Found via web search","why_fit":"","pain_point":"","lead_score":0,"evidence":"","source_url":"","query_used":""}}]}}
"""


# ═══════════════════════════════════════════════════════════════════
# 1. QUERY GENERATION — fully dynamic, never hardcoded
# ═══════════════════════════════════════════════════════════════════

def _extract_target_keywords(idea: str) -> str:
    """Pull customer-facing keywords from the idea (strip product words)."""
    words = re.findall(r"[a-zA-Z]+", idea.lower())
    meaningful = [w for w in words if w not in _PRODUCT_WORDS and len(w) > 2]
    return " ".join(meaningful[:5])


def _generate_search_queries(
    idea: str, icp_data: Dict[str, Any], count: int = 5
) -> List[str]:
    """
    Build up to *count* targeted search queries from the ICP.

    Priority order:
      1. ICP search_queries (best quality — written by OpenAI for this idea)
      2. target_customer_type + "contact"
      3. industry + "business contact page"
      4. ideal_customers segments + "website"
      5. idea-keyword extraction + "contact us"
    """
    queries: List[str] = []

    # ── Strategy 1: ICP-provided search queries (highest quality) ─
    for q in icp_data.get("search_queries", [])[:3]:
        queries.append(q)

    # ── Strategy 2: target customer type ──────────────────────────
    tct = icp_data.get("target_customer_type", "")
    if tct:
        queries.append(f"{tct} contact page")
        queries.append(f"{tct} near me website")

    # ── Strategy 3: industries ────────────────────────────────────
    for ind in icp_data.get("industries", [])[:2]:
        clean = ind.split("/")[0].split("&")[0].strip()
        queries.append(f"{clean} business contact page")

    # ── Strategy 4: ideal customer segments ───────────────────────
    for cust in icp_data.get("ideal_customers", [])[:2]:
        queries.append(f"{cust} contact website")

    # ── Strategy 5: raw idea keywords as a safety net ─────────────
    kw = _extract_target_keywords(idea)
    if kw:
        queries.append(f"{kw} contact us")

    # ── Location-aware variant ────────────────────────────────────
    locations = icp_data.get("location_hints", [])
    if locations and locations[0].lower() not in ("any / global", "global", "any"):
        loc = locations[0]
        if tct:
            queries.append(f"{tct} in {loc} contact")

    # Deduplicate (case-insensitive), limit to count
    seen: set = set()
    unique: List[str] = []
    for q in queries:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    final = unique[:count]
    logger.info("Generated %d search queries: %s", len(final), final)
    return final


# ═══════════════════════════════════════════════════════════════════
# 2. SEARCH COLLECTION
# ═══════════════════════════════════════════════════════════════════

def _collect_search_results(
    queries: List[str], results_per_query: int = 6
) -> List[Dict[str, str]]:
    """Run every query against DuckDuckGo and merge results."""
    if not _DDG_AVAILABLE:
        logger.warning("DuckDuckGo library unavailable — skipping web search")
        return []

    all_results: List[Dict[str, str]] = []
    for query in queries:
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=results_per_query))
            for hit in hits:
                body = hit.get("body", "")
                all_results.append({
                    "title": hit.get("title", ""),
                    "href": hit.get("href", ""),
                    "body": body[:250],
                    "query_used": query,
                })
            logger.info(
                "  Query '%s' → %d results", query, len(hits),
            )
        except Exception as exc:
            logger.error("DuckDuckGo search failed for '%s': %s", query, exc)

    logger.info("Total raw results collected: %d", len(all_results))
    return all_results


# ═══════════════════════════════════════════════════════════════════
# 3. DEDUPLICATION
# ═══════════════════════════════════════════════════════════════════

def _normalise_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return url.lower()


def _deduplicate_results(
    results: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    seen_domains: set = set()
    unique: List[Dict[str, str]] = []
    for r in results:
        domain = _normalise_domain(r.get("href", ""))
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            unique.append(r)
    logger.info("After deduplication: %d results", len(unique))
    return unique


# ═══════════════════════════════════════════════════════════════════
# 4. RELEVANCE FILTERING & SCORING
# ═══════════════════════════════════════════════════════════════════

def _is_blocked(result: Dict[str, str]) -> bool:
    """Return True if a result should be excluded."""
    href = result.get("href", "").lower()
    title = result.get("title", "").lower()

    # Blocked domains
    domain = _normalise_domain(href)
    for bd in BLOCKED_DOMAINS:
        if domain == bd or domain.endswith("." + bd):
            return True

    # Blocked path segments
    for seg in BLOCKED_PATH_KEYWORDS:
        if seg in href:
            return True

    # Listicle / comparison titles
    if LISTICLE_RE.search(title):
        return True

    return False


def _relevance_score(
    result: Dict[str, str],
    icp_data: Dict[str, Any],
    idea: str,
) -> int:
    """
    Score 0-100 indicating how relevant a result is to the ICP.

    Factors:
      - target_customer_type keyword match (+15 per word)
      - industry keyword match (+10 per word)
      - ideal_customer keyword match (+8 per word)
      - idea keyword match (+12 per word)
      - "contact" in text (+5)
      - pain_point keyword match (+6 per word)
    """
    text = (
        result.get("title", "") + " " + result.get("body", "")
    ).lower()

    score = 40  # baseline

    # target_customer_type — strongest signal
    tct = icp_data.get("target_customer_type", "")
    for word in tct.lower().split():
        if len(word) > 3 and word in text:
            score += 15

    # Industry keywords
    for ind in icp_data.get("industries", []):
        for word in ind.lower().split():
            if len(word) > 3 and word in text:
                score += 10

    # Ideal customer segments
    for cust in icp_data.get("ideal_customers", []):
        for word in cust.lower().split():
            if len(word) > 3 and word in text:
                score += 8

    # Idea keywords
    idea_kw = _extract_target_keywords(idea)
    for word in idea_kw.split():
        if len(word) > 3 and word in text:
            score += 12

    # Pain-point keywords
    for pp in icp_data.get("pain_points", []):
        for word in pp.lower().split():
            if len(word) > 4 and word in text:
                score += 6

    # Contact page bonus
    if "contact" in text:
        score += 5

    return min(score, 100)


def _filter_relevant_results(
    results: List[Dict[str, str]],
    icp_data: Dict[str, Any],
    idea: str,
    min_score: int = 45,
) -> List[Dict[str, str]]:
    """Remove blocked results, score remainder, and sort best-first."""
    kept: List[Dict[str, str]] = []
    for r in results:
        if _is_blocked(r):
            continue
        r["_score"] = _relevance_score(r, icp_data, idea)
        if r["_score"] >= min_score:
            kept.append(r)

    kept.sort(key=lambda r: r.get("_score", 0), reverse=True)

    # If strict filtering killed everything, relax the threshold
    if not kept and results:
        logger.warning("Strict filtering removed all results — relaxing")
        for r in results:
            if not _is_blocked(r):
                r["_score"] = _relevance_score(r, icp_data, idea)
                kept.append(r)
        kept.sort(key=lambda r: r.get("_score", 0), reverse=True)

    logger.info("After relevance filtering: %d results", len(kept))
    return kept


# ═══════════════════════════════════════════════════════════════════
# 5. IDEA-SPECIFIC FALLBACK LEADS (no external calls)
# ═══════════════════════════════════════════════════════════════════

def _build_idea_fallback(
    idea: str, icp_data: Dict[str, Any], count: int
) -> List[Dict[str, Any]]:
    """
    Generate demo fallback leads derived from the ICP — never crashes.

    Leads are named after the ICP's target_customer_type and industries
    so they look relevant to the specific idea, NOT generic SaaS companies.
    """
    tct = icp_data.get("target_customer_type", "business")
    industries = icp_data.get("industries", ["General Business"])
    customers = icp_data.get("ideal_customers", ["Small businesses"])
    pain_points = icp_data.get("pain_points", ["Needs better operations"])

    # Build a short label for the business type from target_customer_type
    # e.g. "independent restaurant owners" → "Restaurant"
    tct_words = [
        w.title() for w in tct.split()
        if w.lower() not in (
            "independent", "small", "local", "owners", "operators",
            "managers", "and", "the", "a", "an", "of", "for",
        ) and len(w) > 2
    ]
    biz_label = " ".join(tct_words[:2]) if tct_words else "Business"

    leads: List[Dict[str, Any]] = []
    for i in range(count):
        industry = industries[i % len(industries)]
        customer = customers[i % len(customers)]
        pain = pain_points[i % len(pain_points)]
        prefix = _DEMO_PREFIXES[i % len(_DEMO_PREFIXES)]

        leads.append({
            "company_name": f"{prefix} {biz_label}",
            "website": "Needs verification",
            "location": "Demo",
            "industry": industry,
            "contact_hint": "Demo fallback — run with live search for real results",
            "why_fit": f"Matches target customer: {customer}",
            "pain_point": pain,
            "lead_score": random.randint(60, 78),
            "evidence": "Demo fallback generated from ICP target industry.",
            "source_url": "demo_fallback",
            "query_used": "",
            "source_type": "demo_fallback",
        })

    logger.info(
        "Built %d idea-specific fallback leads (type: %s)",
        len(leads), biz_label,
    )
    return leads


def _fallback_parse(
    results: List[Dict[str, str]], icp_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse raw DDG results directly when OpenAI formatting fails."""
    industry = (
        icp_data.get("industries", ["Technology"])[0]
        if icp_data.get("industries")
        else "Technology"
    )
    pain = (
        icp_data.get("pain_points", ["Needs operational efficiency"])[0]
        if icp_data.get("pain_points")
        else "Needs operational efficiency"
    )

    leads: List[Dict[str, Any]] = []
    for r in results:
        title = r.get("title", "Unknown Company")
        company = title.split("|")[0].split(" - ")[0].strip()[:50]
        body = r.get("body", "")

        leads.append({
            "company_name": company,
            "website": r.get("href", ""),
            "location": "Unknown",
            "industry": industry,
            "contact_hint": "Found via web search",
            "why_fit": body[:120] + ("…" if len(body) > 120 else ""),
            "pain_point": pain,
            "lead_score": min(40 + r.get("_score", 30), 95),
            "evidence": body[:200],
            "source_url": r.get("href", ""),
            "query_used": r.get("query_used", ""),
            "source_type": "web",
        })
    return leads


# ═══════════════════════════════════════════════════════════════════
# 6. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

async def find_prospects(
    idea: str,
    icp_data: Dict[str, Any],
    count: int = 5,
) -> List[Dict[str, Any]]:
    """
    Research prospects for a startup idea.

    Returns a list of lead dicts compatible with the Streamlit UI.
    Guaranteed to never raise — falls back to demo data on any failure.
    """
    count = max(1, min(count, 20))

    # ── Debug banner ─────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PROSPECT AGENT — idea: %s", idea[:120])
    logger.info(
        "  target_customer_type : %s",
        icp_data.get("target_customer_type", "(not set)"),
    )
    logger.info("  industries           : %s", icp_data.get("industries", []))
    logger.info(
        "  ideal_customers      : %s", icp_data.get("ideal_customers", []),
    )
    logger.info(
        "  search_intent        : %s",
        icp_data.get("search_intent", "(not set)"),
    )
    logger.info(
        "  ICP search_queries   : %s", icp_data.get("search_queries", []),
    )

    # ── Step 1: generate queries ─────────────────────────────────
    queries = _generate_search_queries(idea, icp_data, count=5)
    if not queries:
        logger.warning("No queries generated — returning fallback")
        return _build_idea_fallback(idea, icp_data, count)

    # ── Step 2: collect search results ───────────────────────────
    try:
        raw_results = _collect_search_results(queries, results_per_query=6)
    except Exception as exc:
        logger.error("Search collection crashed: %s", exc)
        raw_results = []

    if not raw_results:
        logger.warning("No search results — returning fallback")
        return _build_idea_fallback(idea, icp_data, count)

    # ── Step 3: deduplicate ──────────────────────────────────────
    deduped = _deduplicate_results(raw_results)

    # ── Step 4: relevance filtering ──────────────────────────────
    filtered = _filter_relevant_results(deduped, icp_data, idea)

    if not filtered:
        logger.warning("All results filtered out — returning fallback")
        return _build_idea_fallback(idea, icp_data, count)

    # ── Step 5: format with OpenAI ───────────────────────────────
    # Prepare token-optimised results: top 8 only, minimal keys
    max_to_send = min(len(filtered), 8)
    clean = []
    for r in filtered[:max_to_send]:
        clean.append({
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", "")[:250],
            "q": r.get("query_used", ""),
        })

    pain_points_str = ", ".join(
        icp_data.get("pain_points", [])[: 3]
    )

    prompt = PROSPECT_PROMPT.format(
        idea=idea,
        target_customer_type=icp_data.get(
            "target_customer_type", "target businesses"
        ),
        target_industries=", ".join(icp_data.get("industries", [])),
        pain_points=pain_points_str,
        max_leads=count,
        search_results=_json.dumps(clean, separators=(",", ":")),
    )

    try:
        result = await call_openai_json(
            prompt, temperature=0.2, max_tokens=1200,
        )
        leads = result.get("leads", [])

        if not isinstance(leads, list) or len(leads) == 0:
            logger.warning(
                "LLM returned no leads — falling back to direct parse",
            )
            leads = _fallback_parse(filtered, icp_data)[:count]
        else:
            # Build URL → pre-calculated relevance score map
            url_score_map = {}
            for r in filtered:
                url = r.get("href", "")
                if url:
                    url_score_map[_normalise_domain(url)] = r.get("_score", 50)

            # Normalise every lead and override LLM's lazy scoring
            for lead in leads:
                lead.setdefault("source_type", "web")
                lead.setdefault("contact_hint", "Found via web search")
                lead.setdefault("evidence", "")
                lead.setdefault("source_url", lead.get("website", ""))
                lead.setdefault("query_used", "")

                # Override lead_score with our pre-calculated relevance score
                lead_url = lead.get("website", "") or lead.get("source_url", "")
                lead_domain = _normalise_domain(lead_url) if lead_url else ""
                if lead_domain and lead_domain in url_score_map:
                    lead["lead_score"] = url_score_map[lead_domain]
                else:
                    # If no match found, cap at 80 to avoid fake high scores
                    lead["lead_score"] = min(lead.get("lead_score", 50), 80)

        logger.info(
            "RESULT — %d leads returned (source: web/groq)", len(leads[:count]),
        )
        return leads[:count]

    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        logger.warning("OpenAI formatting failed — direct parse: %s", exc)
        leads = _fallback_parse(filtered, icp_data)[:count]
        logger.info(
            "RESULT — %d leads returned (source: direct parse)", len(leads),
        )
        return leads

    except Exception as exc:
        logger.error("Unexpected error in prospect agent: %s", exc)
        return _build_idea_fallback(idea, icp_data, count)
