"""Recommendation engine — combines keyword, similarity, and taxonomy scores."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


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
) -> Recommendation:
    """Generate a ranked list of partner candidates for a single opportunity.

    Args:
        opportunity_id: Unique opportunity identifier.
        taxonomy_scores: {partner: 0-100} from keyword/taxonomy matching.
        similarity_scores: {partner: 0-100} from similarity to historical opps.
        account_history_scores: {partner: 0-100} from prior deals on same account.
        offer_match_scores: {partner: 0-100} from exact offer/tech field match.
        keywords_by_partner: {partner: [keywords that matched]} for rationale.
        weights: Partner priority weights (tier boost).
        max_candidates: Maximum number of candidates to return.

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

    # Collect all partners that appeared in any signal
    all_partners = (
        set(taxonomy_scores)
        | set(similarity_scores)
        | set(account_history_scores)
        | set(offer_match_scores)
    )

    candidates: list[PartnerCandidate] = []

    for partner in all_partners:
        # Normalize individual signals to 0-100 scale
        keyword_score = taxonomy_scores.get(partner, 0.0)
        # Correlation = how much of taxonomy score comes from this partner vs. spread
        total_tax = sum(taxonomy_scores.values()) or 1
        correlation_score = (keyword_score / total_tax) * 100
        account_history_score = account_history_scores.get(partner, 0.0)
        offer_match_score = offer_match_scores.get(partner, 0.0)

        # Tier boost: weight > 1.0 means tier-1/2, scale to 0-100
        partner_weight = weights.get(partner, 0.8)
        tier_boost = max(0, (partner_weight - 0.8)) * 200  # 1.3 → 100, 1.0 → 40, 0.8 → 0

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

    # Sort by confidence descending, take top N
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    candidates = candidates[:max_candidates]

    return Recommendation(opportunity_id=opportunity_id, candidates=candidates)
