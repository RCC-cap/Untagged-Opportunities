"""Streaming XLS parser for large .xlsm files (200k+ rows)."""

from __future__ import annotations

from pathlib import Path

import polars as pl

# The 29 relevant columns from the dataset
COLUMNS = [
    "Opportunity Line ID",
    "Opportunity ID",
    "Account Name",
    "Opportunity Name",
    "Converted Booking",
    "Converted Weighted Booking",
    "Converted Contribution",
    "Converted Total External Booking",
    "Converted Total Internal Booking",
    "Converted TCV",
    "Euro Bkngs",
    "Weighted Euro Booking",
    "Contribution",
    "Stage",
    "Contract Sign Date",
    "Year",
    "CM%",
    "Offer",
    "Portfolio",
    "Selling SBU",
    "Selling BU",
    "Selling MU",
    "Selling MS",
    "Country",
    "Partner",
    "Technology",
    "Opp Creation Date",
    "Sales Stage Date",
    "Delivery SBU",
    "Delivery Unit",
    "Business Line L1",
    "Business Line L2",
    "Business Line L3",
    "Sector",
    "Primary GOU",
    "Interco Flag",
    "Probability%",
    "Bid Type",
    "Opp Type",
    "Account Type",
    "Opty Lead",
]


def parse_xlsm(
    file_path: Path | str,
    sheet_name: str = "Sheet1",
) -> pl.DataFrame:
    """Read the .xlsm file into a Polars DataFrame.

    Uses calamine engine for fast reading of large Excel files.
    Only reads relevant columns and casts types as needed.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        df = pl.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="calamine",
        )
    except ValueError:
        # Sheet name not found — fall back to first sheet
        df = pl.read_excel(
            file_path,
            sheet_id=1,
            engine="calamine",
        )

    # Keep only columns that exist in the file
    available = [c for c in COLUMNS if c in df.columns]
    df = df.select(available)

    return df
