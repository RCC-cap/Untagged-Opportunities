"""Recommendation engine — LLM-primary with deterministic fallback.

Flow:
1. Compute deterministic signals (keyword, similarity, history, offer match)
2. Call LLM with signals + opportunity context → produces ranked candidates
3. If LLM fails → fall back to deterministic weighted formula

Keyword extraction is retained as a first-class signal that feeds into both
the deterministic formula AND the LLM context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.engine.llm_reasoner import LLMCandidate, reason_partners

logger = logging.getLogger(__name__)


@dataclass
class PartnerCandidate:
    """A single partner recommendation with scoring breakdown."""

    partner: str
    confidence: float
    rationale: str
    signals: dict[str, float] = field(default_factory=dict)


@dataclass
class Recommendation:
    """Full recommendation for one opportunity: ranked list of candidates."""

    opportunity_id: str
    candidates: list[PartnerCandidate]

    @property
    def top_partner(self) -> str:
        return self.candidates[0].partner if self.candidates else "Unknown"

    @property
    def top_confidence(self) -> float:
        return self.candidates[0].confidence if self.candidates else 0.0


def load_partner_weights(config_path: str = "config/partners.yaml") -> dict[str, float]:
    """Load hyperscaler/partner priority weights."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path) as f:
        cfg = yaml.safe_load(f)

    weights: dict[str, float] = {}
    for tier in ("hyperscalers", "strategic", "other"):
        for p in cfg.get("partners", {}).get(tier, []):
            weights[p["name"]] = p["weight"]
    return weights


def _compute_confidence(
    keyword_score: float,
    correlation_score: float,
    account_history_score: float,
    offer_match_score: float,
    tier_boost: float,
) -> float:
    """Compute confidence 0-100 as weighted sum of signals."""
    score = (
        keyword_score * 0.30
        + correlation_score * 0.20
        + account_history_score * 0.30
        + offer_match_score * 0.15
        + tier_boost * 0.05
    )
    return min(round(score, 1), 100.0)


def _build_rationale(partner: str, signals: dict[str, float], keywords_found: list[str]) -> str:
    """Generate human-readable rationale from signal breakdown."""
    parts = []
    if keywords_found:
        parts.append(f"Keywords: {', '.join(repr(k) for k in keywords_found[:5])}")
    if signals.get("offer_match", 0) > 0:
        parts.append("Offer/Technology field matches partner taxonomy")
    if signals.get("account_history", 0) > 0:
        score = signals["account_history"]
        parts.append(f"Account history signal: {score:.0f}/30 pts")
    if signals.get("tier_boost", 0) > 0:
        parts.append("Tier-1 strategic partner boost applied")
    return "; ".join(parts) if parts else "Weak signals — low correlation"


def recommend(
    opportunity_id: str,
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    account_history_scores: dict[str, float] | None = None,
    offer_match_scores: dict[str, float] | None = None,
    keywords_by_partner: dict[str, list[str]] | None = None,
    weights: dict[str, float] | None = None,
    max_candidates: int = 5,
    opportunity_context: dict[str, Any] | None = None,
    keywords: list[str] | None = None,
    taxonomy_context: dict[str, Any] | None = None,
    use_llm: bool = True,
    account_overrides: dict[str, str] | None = None,
) -> Recommendation:
    """Generate a ranked list of partner candidates for a single opportunity.

    Flow: LLM-primary with deterministic fallback.
    1. If use_llm=True, call GPT-5.4 with all signals + context
    2. If LLM succeeds, return its output as the recommendation
    3. If LLM fails (or use_llm=False), fall back to deterministic formula

    Args:
        opportunity_id: Unique opportunity identifier.
        taxonomy_scores: {partner: 0-100} from keyword/taxonomy matching.
        similarity_scores: {partner: 0-100} from similarity to historical opps.
        account_history_scores: {partner: 0-100} from prior deals on same account.
        offer_match_scores: {partner: 0-100} from exact offer/tech field match.
        keywords_by_partner: {partner: [keywords that matched]} for rationale.
        weights: Partner priority weights (tier boost).
        max_candidates: Maximum number of candidates to return.
        opportunity_context: Full opportunity row dict (for LLM context).
        keywords: Extracted keywords from the opportunity (for LLM context).
        taxonomy_context: Taxonomy rules dict (for LLM context).
        use_llm: Whether to attempt LLM reasoning (True) or force deterministic.

    Returns:
        Recommendation with ranked list of PartnerCandidate objects.
    """
    if weights is None:
        weights = load_partner_weights()
    if account_history_scores is None:
        account_history_scores = {}
    if offer_match_scores is None:
        offer_match_scores = {}
    if keywords_by_partner is None:
        keywords_by_partner = {}
    if keywords is None:
        keywords = []
    if account_overrides is None:
        account_overrides = {}

    # ── Check account override (manual knowledge) ──────────────────────
    account_name = str(opportunity_context.get("Account Name", "")) if opportunity_context else ""
    override_partner = account_overrides.get(account_name)
    if override_partner:
        logger.info(f"Account override for {account_name} → {override_partner}")
        return Recommendation(
            opportunity_id=opportunity_id,
            candidates=[
                PartnerCandidate(
                    partner=override_partner,
                    confidence=95.0,
                    rationale=f"{account_name} is transitioning to {override_partner}. Manual override applied based on current account strategy.",
                    signals={"account_override": True},
                )
            ],
        )

    # ── Try LLM-first ──────────────────────────────────────────────────
    if use_llm and opportunity_context:
        llm_result = reason_partners(
            opportunity=opportunity_context,
            keywords=keywords,
            taxonomy_scores=taxonomy_scores,
            similarity_scores=similarity_scores,
            account_history_scores=account_history_scores,
            offer_match_scores=offer_match_scores,
            keywords_by_partner=keywords_by_partner,
            taxonomy_context=taxonomy_context,
        )
        if llm_result:
            candidates = [
                PartnerCandidate(
                    partner=c.partner,
                    confidence=c.confidence,
                    rationale=c.rationale,
                    signals={"llm_reasoned": True},
                )
                for c in llm_result[:max_candidates]
            ]
            logger.info(f"LLM recommendation for {opportunity_id}: {candidates[0].partner} ({candidates[0].confidence}%)")
            return Recommendation(opportunity_id=opportunity_id, candidates=candidates)
        else:
            logger.warning(f"LLM failed for {opportunity_id}, falling back to deterministic")

    # ── Deterministic fallback ─────────────────────────────────────────
    return _deterministic_recommend(
        opportunity_id=opportunity_id,
        taxonomy_scores=taxonomy_scores,
        similarity_scores=similarity_scores,
        account_history_scores=account_history_scores,
        offer_match_scores=offer_match_scores,
        keywords_by_partner=keywords_by_partner,
        weights=weights,
        max_candidates=max_candidates,
    )


def _deterministic_recommend(
    opportunity_id: str,
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    account_history_scores: dict[str, float],
    offer_match_scores: dict[str, float],
    keywords_by_partner: dict[str, list[str]],
    weights: dict[str, float],
    max_candidates: int = 5,
) -> Recommendation:
    """Deterministic weighted-formula recommendation (original logic)."""

    # Collect all partners that appeared in any signal
    all_partners = (
        set(taxonomy_scores)
        | set(similarity_scores)
        | set(account_history_scores)
        | set(offer_match_scores)
    )

    candidates: list[PartnerCandidate] = []

    for partner in all_partners:
        keyword_score = taxonomy_scores.get(partner, 0.0)
        total_tax = sum(taxonomy_scores.values()) or 1
        correlation_score = (keyword_score / total_tax) * 100
        account_history_score = account_history_scores.get(partner, 0.0)
        offer_match_score = offer_match_scores.get(partner, 0.0)

        partner_weight = weights.get(partner, 0.8)
        tier_boost = max(0, (partner_weight - 0.8)) * 200

        signals = {
            "keyword_match": round(keyword_score * 0.30, 1),
            "correlation": round(correlation_score * 0.20, 1),
            "account_history": round(account_history_score * 0.30, 1),
            "offer_match": round(offer_match_score * 0.15, 1),
            "tier_boost": round(tier_boost * 0.05, 1),
        }

        confidence = _compute_confidence(
            keyword_score, correlation_score, account_history_score,
            offer_match_score, tier_boost,
        )

        rationale = _build_rationale(
            partner, signals, keywords_by_partner.get(partner, [])
        )

        candidates.append(PartnerCandidate(
            partner=partner,
            confidence=confidence,
            rationale=rationale,
            signals=signals,
        ))

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    candidates = candidates[:max_candidates]

    # Never return empty — provide a "no match" placeholder so the email
    # can show a clear message asking the lead to suggest a partner.
    if not candidates:
        candidates = [
            PartnerCandidate(
                partner="Unknown",
                confidence=0.0,
                rationale="Insufficient signals to recommend a partner. Please suggest the correct partner based on your deal knowledge.",
                signals={"no_signal": True},
            )
        ]

    return Recommendation(opportunity_id=opportunity_id, candidates=candidates)
