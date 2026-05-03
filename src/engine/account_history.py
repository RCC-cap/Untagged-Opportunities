"""Account history scoring — boost partners based on prior tagged deals."""

from __future__ import annotations

import polars as pl


def score_account_history(
    account_name: str,
    tagged_df: pl.DataFrame,
    partner_column: str = "Partner",
    account_column: str = "Account Name",
    min_deals_for_boost: int = 2,
) -> dict[str, float]:
    """Score partners based on historical deals for the same account.

    If Contoso AG has 10 prior Microsoft-tagged deals out of 12 total,
    Microsoft gets a score of (10/12) * 100 = 83.3.

    Args:
        account_name: The account to look up.
        tagged_df: DataFrame of all tagged opportunities (Partner != untagged).
        partner_column: Name of the partner column.
        account_column: Name of the account column.
        min_deals_for_boost: Minimum prior deals to trigger scoring.

    Returns:
        Dict of {partner_name: score_0_to_100} sorted descending.
    """
    if not account_name or str(account_name).strip() in ("", "-", "None"):
        return {}

    # Filter to same account, only tagged rows
    account_deals = tagged_df.filter(
        (pl.col(account_column).cast(pl.Utf8) == str(account_name))
        & pl.col(partner_column).is_not_null()
        & ~pl.col(partner_column).cast(pl.Utf8).is_in(["No Vendor/Partner", "-", ""])
    )

    if account_deals.height < min_deals_for_boost:
        return {}

    # Count deals per partner
    partner_counts = (
        account_deals.group_by(partner_column)
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    total_deals = account_deals.height
    scores: dict[str, float] = {}

    for row in partner_counts.iter_rows(named=True):
        partner = row[partner_column]
        count = row["count"]
        # Score = ratio of deals for this partner × 100
        scores[partner] = round((count / total_deals) * 100, 1)

    return scores
