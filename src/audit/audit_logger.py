"""Audit logging for all retagging actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def append_audit_entry(
    opportunity_id: str,
    recommended_partner: str,
    decision: str,
    rationale: str,
    confidence: float,
    responded_by: str | None = None,
    override_partner: str | None = None,
    log_path: str = "data/audit_log.jsonl",
) -> None:
    """Append a single audit entry as a JSON line.

    Each line is a self-contained JSON object for easy streaming reads.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "opportunity_id": str(opportunity_id),
        "recommended_partner": recommended_partner,
        "decision": decision,
        "confidence": round(confidence, 1),
        "rationale": rationale,
        "responded_by": responded_by,
        "override_partner": override_partner,
    }

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_audit_log(log_path: str = "data/audit_log.jsonl") -> list[dict]:
    """Read the full audit log into a list of dicts."""
    path = Path(log_path)
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def get_processed_ids(log_path: str = "data/audit_log.jsonl") -> set[str]:
    """Return set of Opportunity IDs already processed (for delta logic)."""
    entries = read_audit_log(log_path)
    return {e["opportunity_id"] for e in entries}
