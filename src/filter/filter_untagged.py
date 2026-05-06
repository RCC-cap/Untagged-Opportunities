"""Filter untagged opportunities from the parsed DataFrame."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import yaml

UNTAGGED_VALUES = {"No Vendor/Partner", "-", "", None, "Open Source", "Capgemini"}


def load_untagged_values(config_path: str = "config/partners.yaml") -> set[str]:
    """Load the list of values that identify untagged opportunities."""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f)
        return set(cfg.get("untagged_values", UNTAGGED_VALUES))
    return UNTAGGED_VALUES


def filter_untagged(
    df: pl.DataFrame,
    partner_column: str = "Partner",
    processed_ids: set[str] | None = None,
) -> pl.DataFrame:
    """Return only rows where Partner is untagged and not already processed.

    Args:
        df: Full DataFrame from xls_parser.
        partner_column: Name of the partner column.
        processed_ids: Set of Opportunity IDs already processed (delta logic).

    Returns:
        Filtered DataFrame with untagged rows only.
    """
    untagged_vals = load_untagged_values()

    mask = (
        pl.col(partner_column).is_null()
        | pl.col(partner_column).cast(pl.Utf8).is_in(list(untagged_vals))
    )
    filtered = df.filter(mask)

    # Delta: exclude already-processed IDs
    if processed_ids and "Opportunity ID" in filtered.columns:
        filtered = filtered.filter(
            ~pl.col("Opportunity ID").cast(pl.Utf8).is_in(list(processed_ids))
        )

    return filtered
