"""
Research Agent — gathers information about a startup before outreach.
"""


class ResearchAgent:
    """Agent responsible for researching startups and their key contacts."""

    async def research_startup(self, startup_name: str) -> dict:
        """
        Research a startup and return structured information.

        Returns:
            dict with keys: summary, funding, founders, recent_news
        """
        # TODO: integrate web search / scraping / API calls
        return {
            "summary": f"{startup_name} is an innovative startup.",
            "funding": "Unknown",
            "founders": [],
            "recent_news": [],
        }
