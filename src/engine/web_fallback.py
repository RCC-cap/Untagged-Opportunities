"""Web search fallback — uses Azure OpenAI to research company partnerships.

When the recommendation engine cannot confidently match a partner from internal
data, this module asks the LLM to reason about publicly known partnerships,
technology alliances, and recent news for the account/opportunity.

Returns structured insight: suggested partner, confidence, and explanation.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_WEB_SEARCH_PROMPT = """\
You are a technology partnerships research analyst. Given a company name and
opportunity description, identify the most likely technology partner
(e.g., Microsoft, AWS, SAP, Google, Oracle, ServiceNow, Salesforce) based on
your knowledge of:
- The company's known technology stack and cloud strategy
- Recent partnership announcements or press releases
- Industry-typical vendor choices for that company's sector

Respond ONLY with valid JSON in this exact format:
{"partner": "PartnerName", "confidence": 35, "insight": "One sentence explanation."}

Rules:
- partner: the single most likely partner name (proper case)
- confidence: integer 15-45 (you are uncertain — this is a suggestion, not a match)
- insight: 1 sentence factual explanation of why

If you truly have no idea, return: {"partner": "", "confidence": 0, "insight": ""}
Do NOT make things up. Only state facts you are confident about.
"""


@dataclass
class WebFallbackResult:
    """Structured result from web/LLM partner research."""

    partner: str
    confidence: float
    insight: str


def search_partner_insight(
    account_name: str,
    opp_name: str,
    sector: str = "",
    country: str = "",
    offer: str = "",
) -> WebFallbackResult:
    """Ask Azure OpenAI about likely technology partnerships for this account.

    Args:
        account_name: Company/account name (e.g. "GSK | BE")
        opp_name: Opportunity name for additional context
        sector: Industry sector if available
        country: Country for geographic context
        offer: Offer/technology field if available

    Returns:
        WebFallbackResult with partner, confidence (15-45%), and insight text.
    """
    empty = WebFallbackResult(partner="", confidence=0, insight="")

    # Extract clean company name (strip country codes like "| BE")
    clean_name = account_name.split("|")[0].strip() if "|" in account_name else account_name

    user_msg = f"Company: {clean_name}\n"
    if sector:
        user_msg += f"Sector: {sector}\n"
    if country:
        user_msg += f"Country: {country}\n"
    if offer:
        user_msg += f"Technology/Offer: {offer}\n"
    user_msg += f"Opportunity: {opp_name}\n\n"
    user_msg += "What technology partner is this company most likely aligned with?"

    try:
        client = _get_client()
        if client is None:
            return empty

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _WEB_SEARCH_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```" in content:
                content = content.split("```")[1].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
                data = json.loads(content)
            else:
                logger.warning(f"Web fallback: non-JSON response for {clean_name}: {content[:80]}")
                return empty

        partner = str(data.get("partner", "")).strip()
        confidence = min(45, max(0, int(data.get("confidence", 0))))
        insight = str(data.get("insight", "")).strip()

        # Filter out unhelpful responses
        if not partner or confidence == 0:
            logger.info(f"Web fallback: no useful insight for {clean_name}")
            return empty

        low = insight.lower()
        if any(phrase in low for phrase in ["i don't have", "i cannot", "not sure", "no specific", "unable to"]):
            logger.info(f"Web fallback: uncertain response for {clean_name}")
            return empty

        logger.info(f"Web fallback for {clean_name}: {partner} ({confidence}%) — {insight[:60]}...")
        return WebFallbackResult(partner=partner, confidence=confidence, insight=insight)

    except Exception as e:
        logger.warning(f"Web fallback failed for {clean_name}: {e}")
        return empty


def _get_client() -> AzureOpenAI | None:
    """Create Azure OpenAI client from environment variables."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_KEY")
    if not endpoint or not key:
        logger.warning("Azure OpenAI not configured for web fallback")
        return None

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )
