"""LLM Reasoner — GPT-5.4 as primary partner-tagging analyst.

Receives pre-computed deterministic signals (keywords, taxonomy scores,
similarity scores, account history, offer matches) plus raw opportunity
context. Produces a ranked list of partner candidates with confidence
scores and natural-language rationale.

Falls back to None if the LLM call fails, allowing the caller to use
the deterministic formula instead.
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

SYSTEM_PROMPT = """\
You are the Thor Partner Tagging Agent — an AI analyst that assigns the correct
technology partner to untagged enterprise sales opportunities at Capgemini.

Your job: given an untagged sales opportunity and pre-computed scoring signals,
determine the correct technology partner to assign. Produce a ranked list of
1-3 partner candidates with detailed, evidence-based rationale.

## Input you receive
- **Opportunity fields**: ID, Name, Account, Offer, Technology, Portfolio, Sector, Country
- **Extracted keywords**: tokens found in the opportunity text
- **Taxonomy scores**: how well keywords match each partner's known keyword set (0-100)
- **Similarity scores**: how similar this opp is to historically-tagged opps per partner (0-100)
- **Account history scores**: what % of prior deals for this account went to each partner (0-100)
- **Offer/Tech match scores**: exact match between Offer/Technology fields and partner products (0-100)
- **Taxonomy rules context**: the keyword lists and products associated with each partner

## Scoring rules
- Account history is the STRONGEST signal. If 80%+ of prior deals on this account belong
  to one partner, that partner should rank #1 unless there is very strong contradicting evidence.
- Keyword matches in Offer and Technology fields are strong indicators.
- If keywords point to multiple partners, use the business context (opportunity name,
  sector, account type) to disambiguate.
- If signals conflict, explain the conflict in the rationale.
- Be precise with confidence scores:
  - 80-100: high certainty (multiple converging signals)
  - 50-79: moderate (some signals, not all converge)
  - 0-49: best guess (weak or conflicting signals)

## Rationale guidelines
Write rationale that a Sales Lead can trust and act on. Each rationale MUST:
1. Cite the specific evidence (e.g. "78% of prior deals on this account are tagged Microsoft")
2. Mention which scoring signals support the recommendation (account history, keywords, taxonomy, similarity)
3. Explain the business fit briefly (e.g. "Azure migration aligns with the Cloud & Custom Apps offer")
4. Be 2-4 sentences long — enough to justify the tag but concise enough to scan quickly

## Output format
Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{
  "candidates": [
    {
      "partner": "Partner Name",
      "confidence": 82,
      "rationale": "2-4 sentence evidence-based rationale explaining WHY this partner fits"
    }
  ],
  "reasoning": "Brief overall reasoning about how you weighed the signals"
}

Order candidates by confidence (highest first). Maximum 3 candidates.
Only include partners where you have at least some evidence (confidence > 10).
"""


@dataclass
class LLMCandidate:
    """A partner candidate produced by the LLM."""

    partner: str
    confidence: float
    rationale: str


def reason_partners(
    opportunity: dict[str, Any],
    keywords: list[str],
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    account_history_scores: dict[str, float],
    offer_match_scores: dict[str, float],
    keywords_by_partner: dict[str, list[str]],
    taxonomy_context: dict[str, Any] | None = None,
) -> list[LLMCandidate] | None:
    """Call GPT-5.4 to reason about partner assignment.

    Args:
        opportunity: Dict of opportunity fields (Name, Account, Offer, Tech, etc.)
        keywords: Extracted keywords from the opportunity
        taxonomy_scores: {partner: 0-100} from keyword-taxonomy matching
        similarity_scores: {partner: 0-100} from historical similarity
        account_history_scores: {partner: 0-100} from prior deals on same account
        offer_match_scores: {partner: 0-100} from exact Offer/Tech field matching
        keywords_by_partner: {partner: [matched_keywords]} showing which keywords hit
        taxonomy_context: Optional taxonomy rules for context (partner -> keywords/products)

    Returns:
        List of LLMCandidate sorted by confidence (highest first), or None if call fails.
    """
    user_message = _build_user_message(
        opportunity=opportunity,
        keywords=keywords,
        taxonomy_scores=taxonomy_scores,
        similarity_scores=similarity_scores,
        account_history_scores=account_history_scores,
        offer_match_scores=offer_match_scores,
        keywords_by_partner=keywords_by_partner,
        taxonomy_context=taxonomy_context,
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty content")
            return None

        return _parse_response(content)

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


def reason_partners_batch(
    opportunities: list[dict[str, Any]],
) -> list[list[LLMCandidate] | None]:
    """Process multiple opportunities in a single LLM call.

    Sends up to 10 opportunities per call to reduce API usage.
    Each opportunity dict must contain: 'opportunity', 'keywords',
    'taxonomy_scores', 'similarity_scores', 'account_history_scores',
    'offer_match_scores', 'keywords_by_partner'.

    Returns:
        List of results (one per opportunity), or None for failed parses.
    """
    if not opportunities:
        return []

    batch_message = _build_batch_message(opportunities)

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + _BATCH_ADDENDUM},
                {"role": "user", "content": batch_message},
            ],
            temperature=0.2,
            max_tokens=min(800 * len(opportunities), 4096),
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty content for batch")
            return [None] * len(opportunities)

        return _parse_batch_response(content, len(opportunities))

    except Exception as e:
        logger.error(f"LLM batch call failed: {e}")
        return [None] * len(opportunities)


# ── Private helpers ────────────────────────────────────────────────────


_client: AzureOpenAI | None = None

_BATCH_ADDENDUM = """

## Batch mode
You will receive MULTIPLE opportunities in one message. Respond with:
{
  "results": [
    {
      "opp_id": "...",
      "candidates": [...],
      "reasoning": "..."
    }
  ]
}
One entry per opportunity, in the same order as received.
"""


def _get_client() -> AzureOpenAI:
    """Lazy-init Azure OpenAI client."""
    global _client
    if _client is not None:
        return _client

    _client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ.get("AZURE_OPENAI_KEY") or os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )
    return _client


def _build_user_message(
    opportunity: dict[str, Any],
    keywords: list[str],
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    account_history_scores: dict[str, float],
    offer_match_scores: dict[str, float],
    keywords_by_partner: dict[str, list[str]],
    taxonomy_context: dict[str, Any] | None = None,
) -> str:
    """Build the structured user message for a single opportunity."""
    payload = {
        "opportunity": {
            "id": opportunity.get("Opportunity ID", ""),
            "name": opportunity.get("Opportunity Name", ""),
            "account": opportunity.get("Account Name", ""),
            "offer": opportunity.get("Offer", ""),
            "technology": opportunity.get("Technology", ""),
            "portfolio": opportunity.get("Portfolio", ""),
            "sector": opportunity.get("Sector", ""),
            "country": opportunity.get("Account Country", opportunity.get("Country", "")),
            "business_line": opportunity.get("Business Line Level 1", opportunity.get("Business Line L1", "")),
            "gen_ai_technology": opportunity.get("Gen AI Technology", ""),
        },
        "extracted_keywords": keywords,
        "signals": {
            "taxonomy_scores": taxonomy_scores,
            "similarity_scores": similarity_scores,
            "account_history_scores": account_history_scores,
            "offer_match_scores": offer_match_scores,
        },
        "keywords_matched_per_partner": keywords_by_partner,
    }

    if taxonomy_context:
        # Include a summary (not full rules — too large)
        summary = {}
        for partner, rule in taxonomy_context.get("rules", {}).items():
            summary[partner] = {
                "keywords_sample": rule.get("keywords", [])[:10],
                "technologies": rule.get("technologies", []),
                "offers": rule.get("offers", []),
            }
        payload["taxonomy_context"] = summary

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_batch_message(opportunities: list[dict[str, Any]]) -> str:
    """Build a batch message for multiple opportunities."""
    batch = []
    for opp_data in opportunities:
        batch.append({
            "opportunity": {
                "id": opp_data["opportunity"].get("Opportunity ID", ""),
                "name": opp_data["opportunity"].get("Opportunity Name", ""),
                "account": opp_data["opportunity"].get("Account Name", ""),
                "offer": opp_data["opportunity"].get("Offer", ""),
                "technology": opp_data["opportunity"].get("Technology", ""),
                "portfolio": opp_data["opportunity"].get("Portfolio", ""),
                "sector": opp_data["opportunity"].get("Sector", ""),
                "country": opp_data["opportunity"].get("Country", ""),
            },
            "extracted_keywords": opp_data.get("keywords", []),
            "signals": {
                "taxonomy_scores": opp_data.get("taxonomy_scores", {}),
                "similarity_scores": opp_data.get("similarity_scores", {}),
                "account_history_scores": opp_data.get("account_history_scores", {}),
                "offer_match_scores": opp_data.get("offer_match_scores", {}),
            },
            "keywords_matched_per_partner": opp_data.get("keywords_by_partner", {}),
        })
    return json.dumps({"opportunities": batch}, ensure_ascii=False, indent=2)


def _parse_response(content: str) -> list[LLMCandidate] | None:
    """Parse single-opportunity LLM response."""
    try:
        data = json.loads(content)
        candidates = []
        for c in data.get("candidates", []):
            candidates.append(LLMCandidate(
                partner=str(c.get("partner", "")),
                confidence=float(c.get("confidence", 0)),
                rationale=str(c.get("rationale", "")),
            ))
        return sorted(candidates, key=lambda x: x.confidence, reverse=True) or None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None


def _parse_batch_response(
    content: str, expected_count: int
) -> list[list[LLMCandidate] | None]:
    """Parse batch LLM response."""
    try:
        data = json.loads(content)
        results = []
        for item in data.get("results", []):
            candidates = []
            for c in item.get("candidates", []):
                candidates.append(LLMCandidate(
                    partner=str(c.get("partner", "")),
                    confidence=float(c.get("confidence", 0)),
                    rationale=str(c.get("rationale", "")),
                ))
            results.append(
                sorted(candidates, key=lambda x: x.confidence, reverse=True) or None
            )

        # Pad with None if LLM returned fewer results
        while len(results) < expected_count:
            results.append(None)
        return results

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse LLM batch response: {e}")
        return [None] * expected_count
