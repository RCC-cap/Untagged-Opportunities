"""Similarity scoring against historically tagged opportunities."""

from __future__ import annotations

import polars as pl


def score_similarity(
    untagged_row: dict,
    tagged_df: pl.DataFrame,
    match_columns: list[str] | None = None,
) -> dict[str, float]:
    """Score how similar an untagged row is to tagged rows, grouped by partner.

    Uses exact-match counting on key fields (Offer, Portfolio, Technology,
    Sector, Country) to find the most common partner for similar opportunities.

    Returns:
        Dict of {partner_name: similarity_score} sorted descending.
    """
    if match_columns is None:
        match_columns = ["Offer", "Portfolio", "Technology", "Sector", "Country"]

    available_cols = [c for c in match_columns if c in tagged_df.columns]
    if not available_cols:
        return {}

    # Build filter: count matches on each column
    scores: dict[str, float] = {}
    for col in available_cols:
        val = untagged_row.get(col)
        if not val or str(val).strip() in ("", "-", "None"):
            continue
        matches = tagged_df.filter(pl.col(col).cast(pl.Utf8) == str(val))
        if matches.is_empty():
            continue
        # Count partner occurrences in matching rows
        partner_counts = (
            matches.group_by("Partner")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
        )
        for row in partner_counts.iter_rows(named=True):
            partner = row["Partner"]
            count = row["count"]
            scores[partner] = scores.get(partner, 0.0) + count

    # Normalize to 0-100
    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: round((v / max_score) * 100, 1) for k, v in scores.items()}

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
