"""Taxonomy-based partner mapping using configurable rules."""

from __future__ import annotations

import json
from pathlib import Path


def load_taxonomy(config_path: str = "config/taxonomy.json") -> dict:
    """Load taxonomy rules from JSON config."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy config not found: {path}")
    with open(path) as f:
        return json.load(f)


def match_taxonomy(
    keywords: list[str],
    taxonomy: dict | None = None,
) -> dict[str, float]:
    """Match keywords against taxonomy rules.

    Returns:
        Dict of {partner_name: match_score} based on keyword hits.
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    rules = taxonomy.get("rules", {})
    scores: dict[str, float] = {}

    keywords_lower = [k.lower() for k in keywords]
    text_joined = " ".join(keywords_lower)

    for partner, rule in rules.items():
        hit_count = 0
        partner_keywords = rule.get("keywords", [])
        for kw in partner_keywords:
            if kw.lower() in text_joined:
                hit_count += 1

        if hit_count > 0:
            # Score based on proportion of keyword matches
            max_possible = len(partner_keywords) if partner_keywords else 1
            scores[partner] = round((hit_count / max_possible) * 100, 1)

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
