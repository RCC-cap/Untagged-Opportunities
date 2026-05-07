"""Business-level state management backed by Cosmos DB.

Tracks: recommendations made, emails sent, user responses.
Replaces the local JSONL-based audit_logger for state queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.store.cosmos_client import query_documents, upsert_document


# ── Write Operations ───────────────────────────────────────────────────


def record_recommendation(
    opp_id: str,
    candidates: list[dict[str, Any]],
    top_partner: str,
    top_confidence: float,
) -> None:
    """Record that a recommendation was generated for an opportunity."""
    upsert_document({
        "id": f"rec-{opp_id}",
        "opp_id": opp_id,
        "type": "recommendation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candidates": candidates,
        "top_partner": top_partner,
        "top_confidence": round(top_confidence, 1),
    })


def record_email_sent(
    opp_id: str,
    lead_email: str,
    token_expiry: str | None = None,
) -> None:
    """Record that an approval email was sent for this opportunity."""
    upsert_document({
        "id": f"email-{opp_id}",
        "opp_id": opp_id,
        "type": "email_sent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead_email": lead_email,
        "token_expiry": token_expiry,
    })


def record_response(
    opp_id: str,
    decision: str,
    selected_partner: str | None = None,
    responded_by: str | None = None,
    comment: str | None = None,
) -> None:
    """Record a Sales Lead's response (select, suggest, or comment)."""
    doc = {
        "id": f"resp-{opp_id}",
        "opp_id": opp_id,
        "type": "response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "selected_partner": selected_partner,
        "responded_by": responded_by,
    }
    if comment:
        doc["comment"] = comment
    upsert_document(doc)


# ── Query Operations ──────────────────────────────────────────────────


def get_processed_ids() -> set[str]:
    """Return set of opportunity IDs that already have a recommendation."""
    docs = query_documents(
        query="SELECT c.opp_id FROM c WHERE c.type = 'recommendation'",
    )
    return {doc["opp_id"] for doc in docs}


def is_email_sent(opp_id: str) -> bool:
    """Check if an approval email has already been sent for this opp."""
    docs = query_documents(
        query="SELECT c.id FROM c WHERE c.type = 'email_sent' AND c.opp_id = @opp_id",
        parameters=[{"name": "@opp_id", "value": opp_id}],
        partition_key=opp_id,
    )
    return len(docs) > 0


def is_responded(opp_id: str) -> bool:
    """Check if the Sales Lead has already responded for this opp."""
    docs = query_documents(
        query="SELECT c.id FROM c WHERE c.type = 'response' AND c.opp_id = @opp_id",
        parameters=[{"name": "@opp_id", "value": opp_id}],
        partition_key=opp_id,
    )
    return len(docs) > 0


def get_response(opp_id: str) -> dict[str, Any] | None:
    """Get the response record for an opportunity (if any)."""
    docs = query_documents(
        query="SELECT * FROM c WHERE c.type = 'response' AND c.opp_id = @opp_id",
        parameters=[{"name": "@opp_id", "value": opp_id}],
        partition_key=opp_id,
    )
    return docs[0] if docs else None


def get_pending_for_lead(lead_email: str) -> list[dict[str, Any]]:
    """Get all opps where email was sent to this lead but no response yet.

    Cross-partition query (lead_email is not the partition key).
    """
    sent_docs = query_documents(
        query="SELECT c.opp_id FROM c WHERE c.type = 'email_sent' AND c.lead_email = @email",
        parameters=[{"name": "@email", "value": lead_email}],
    )
    sent_ids = {doc["opp_id"] for doc in sent_docs}

    if not sent_ids:
        return []

    responded_docs = query_documents(
        query="SELECT c.opp_id FROM c WHERE c.type = 'response'",
    )
    responded_ids = {doc["opp_id"] for doc in responded_docs}

    pending_ids = sent_ids - responded_ids
    return [{"opp_id": oid} for oid in pending_ids]
