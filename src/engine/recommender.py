"""Recommendation engine — combines keyword, similarity, and taxonomy scores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Recommendation:
    opportunity_id: str
    primary_partner: str
    secondary_partner: str | None
    confidence: float
    rationale: str


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


def combine_scores(
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Combine taxonomy and similarity scores with partner weights.

    Formula: final = (taxonomy * 0.4 + similarity * 0.6) * weight
    """
    if weights is None:
        weights = load_partner_weights()

    all_partners = set(taxonomy_scores) | set(similarity_scores)
    combined: dict[str, float] = {}

    for partner in all_partners:
        tax = taxonomy_scores.get(partner, 0.0)
        sim = similarity_scores.get(partner, 0.0)
        weight = weights.get(partner, 0.8)
        score = (tax * 0.4 + sim * 0.6) * weight
        combined[partner] = round(score, 1)

    return dict(sorted(combined.items(), key=lambda x: x[1], reverse=True))


def recommend(
    opportunity_id: str,
    taxonomy_scores: dict[str, float],
    similarity_scores: dict[str, float],
    rationale: str = "",
) -> Recommendation:
    """Generate a partner recommendation for a single opportunity."""
    combined = combine_scores(taxonomy_scores, similarity_scores)

    partners = list(combined.keys())
    scores = list(combined.values())

    primary = partners[0] if partners else "Unknown"
    confidence = scores[0] if scores else 0.0
    secondary = partners[1] if len(partners) > 1 else None

    return Recommendation(
        opportunity_id=opportunity_id,
        primary_partner=primary,
        secondary_partner=secondary,
        confidence=min(confidence, 100.0),
        rationale=rationale,
    )
