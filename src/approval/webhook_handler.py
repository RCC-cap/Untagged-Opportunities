"""Webhook handler for capturing approval/rejection responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ApprovalResponse:
    opportunity_id: str
    decision: str  # "approve" | "reject" | "override"
    partner: str | None
    override_partner: str | None
    feedback: str | None
    responded_by: str | None
    responded_at: datetime


def parse_webhook_payload(payload: dict) -> ApprovalResponse:
    """Parse an incoming webhook payload into an ApprovalResponse.

    Expected query params / body:
        opp_id: str
        decision: "approve" | "reject" | "override"
        partner: str (the recommended partner)
        override_partner: str (if decision == override)
        feedback: str (optional)
        responded_by: str (email of responder)
    """
    return ApprovalResponse(
        opportunity_id=str(payload.get("opp_id", "")),
        decision=payload.get("decision", "reject"),
        partner=payload.get("partner"),
        override_partner=payload.get("override_partner"),
        feedback=payload.get("feedback"),
        responded_by=payload.get("responded_by"),
        responded_at=datetime.now(timezone.utc),
    )
