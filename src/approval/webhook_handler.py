"""Webhook handler for capturing partner selection / rejection responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.approval.token_utils import verify_token
from src.audit.audit_logger import append_audit_entry
from src.update.dataset_updater import update_sharepoint_file


@dataclass
class SelectionResponse:
    """Parsed webhook response from a Sales Lead click."""

    opportunity_id: str
    decision: str  # "select" | "reject"
    partner: str | None  # Which partner was selected (None if reject)
    responded_at: datetime
    valid: bool  # Whether token verification passed


def handle_select(params: dict) -> tuple[str, int]:
    """Handle a partner selection webhook call.

    Expected query params:
        opp_id: str
        partner: str
        token: str

    Returns:
        (html_response, status_code)
    """
    opp_id = params.get("opp_id", "")
    partner = params.get("partner", "")
    token = params.get("token", "")

    if not opp_id or not partner or not token:
        return _error_page("Missing required parameters."), 400

    if not verify_token(opp_id, partner, token):
        return _error_page("Invalid or expired link. Please contact your administrator."), 403

    # Log to audit
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner=partner,
        decision="selected",
        rationale=f"Sales Lead selected {partner} from email",
        confidence=0,  # Not relevant for the response
    )

    # TODO: Write tag back to dataset
    # update_partner_in_source(opp_id, partner)

    return _success_page(opp_id, partner), 200


def handle_reject(params: dict) -> tuple[str, int]:
    """Handle a reject-all webhook call.

    Expected query params:
        opp_id: str
        token: str

    Returns:
        (html_response, status_code)
    """
    opp_id = params.get("opp_id", "")
    token = params.get("token", "")

    if not opp_id or not token:
        return _error_page("Missing required parameters."), 400

    if not verify_token(opp_id, "", token):
        return _error_page("Invalid or expired link. Please contact your administrator."), 403

    # Log to audit
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner="",
        decision="rejected",
        rationale="Sales Lead rejected all partner suggestions",
        confidence=0,
    )

    return _reject_page(opp_id), 200


def _success_page(opp_id: str, partner: str) -> str:
    """Render confirmation page after partner selection."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Tag Applied</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #107c10;">✅ Tag Applied Successfully</h2>
  <p>Partner tag <strong>{partner}</strong> has been applied to opportunity <strong>{opp_id}</strong>.</p>
  <p style="color: #666; margin-top: 24px;">You may close this window.</p>
</body>
</html>"""


def _reject_page(opp_id: str) -> str:
    """Render confirmation page after reject-all."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Rejected</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #d83b01;">❌ All Recommendations Rejected</h2>
  <p>No partner has been applied to opportunity <strong>{opp_id}</strong>.</p>
  <p>This opportunity has been flagged for manual review by Sales Operations.</p>
  <p style="color: #666; margin-top: 24px;">You may close this window.</p>
</body>
</html>"""


def _error_page(message: str) -> str:
    """Render error page."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #d83b01;">⚠️ Error</h2>
  <p>{message}</p>
</body>
</html>"""
