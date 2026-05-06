"""Keyword extraction from opportunity fields."""

from __future__ import annotations

import re


def extract_keywords(row: dict) -> list[str]:
    """Extract relevant keywords from an opportunity row.

    Combines text from: Opportunity Name, Offer, Portfolio, Technology.
    Returns lowercase, deduplicated keyword list.
    """
    text_fields = [
        row.get("Opportunity Name", ""),
        row.get("Offer", ""),
        row.get("Portfolio", ""),
        row.get("Technology", ""),
        row.get("Account Name", ""),
        row.get("Gen AI Technology", ""),
        row.get("Sector", ""),
    ]

    combined = " ".join(str(f) for f in text_fields if f)
    combined = combined.lower()

    # Remove special chars, keep alphanumeric + spaces + slashes (for S/4HANA etc.)
    combined = re.sub(r"[^a-z0-9\s/\-]", " ", combined)

    # Split and deduplicate
    tokens = combined.split()
    # Remove very short tokens
    tokens = [t for t in tokens if len(t) > 1]

    return list(dict.fromkeys(tokens))  # preserve order, deduplicate
