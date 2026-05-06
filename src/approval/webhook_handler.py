"""Webhook handler for capturing partner selection / rejection responses."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone

from src.approval.token_utils import verify_token
from src.audit.audit_logger import append_audit_entry
from src.extract.blob_writer import record_decision_to_blob, sync_audit_to_blob
from src.store.state_manager import record_response


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

    # Persist to Cosmos DB
    record_response(
        opp_id=opp_id,
        decision="selected",
        selected_partner=partner,
    )

    # Persist to Blob Storage (survives redeploys)
    record_decision_to_blob(opp_id=opp_id, decision="selected", partner=partner)

    # Local audit backup
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner=partner,
        decision="selected",
        rationale=f"Sales Lead selected {partner} from email",
        confidence=0,
    )
    sync_audit_to_blob()

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

    # Persist to Cosmos DB
    record_response(
        opp_id=opp_id,
        decision="rejected",
        selected_partner=None,
    )

    # Persist to Blob Storage (survives redeploys)
    record_decision_to_blob(opp_id=opp_id, decision="rejected", partner=None)

    # Local audit backup
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner="",
        decision="rejected",
        rationale="Sales Lead rejected all partner suggestions",
        confidence=0,
    )
    sync_audit_to_blob()

    return _reject_page(opp_id), 200


def _success_page(opp_id: str, partner: str) -> str:
    """Render confirmation page after partner selection."""
    safe_opp = html.escape(opp_id)
    safe_partner = html.escape(partner)
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Tag Applied</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #107c10;">✅ Tag Applied Successfully</h2>
  <p>Partner tag <strong>{safe_partner}</strong> has been applied to opportunity <strong>{safe_opp}</strong>.</p>
  <p style="color: #666; margin-top: 24px;">You may close this window.</p>
</body>
</html>"""


def _reject_page(opp_id: str) -> str:
    """Render confirmation page after reject-all."""
    safe_opp = html.escape(opp_id)
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Rejected</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #d83b01;">❌ All Recommendations Rejected</h2>
  <p>No partner has been applied to opportunity <strong>{safe_opp}</strong>.</p>
  <p>This opportunity has been flagged for manual review by Sales Operations.</p>
  <p style="color: #666; margin-top: 24px;">You may close this window.</p>
</body>
</html>"""


def _error_page(message: str) -> str:
    """Render error page."""
    safe_msg = html.escape(message)
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #d83b01;">⚠️ Error</h2>
  <p>{safe_msg}</p>
</body>
</html>"""


def render_suggest_form(opp_id: str, token: str) -> str:
    """Render the 'Suggest a different partner' HTML form."""
    safe_opp = html.escape(opp_id)
    safe_token = html.escape(token)
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"><title>Suggest Partner — THOR</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 40px 20px; background: #eef1f6; font-family: 'Ubuntu', 'Segoe UI', sans-serif;">
  <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.10); overflow: hidden;">
    <div style="background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); padding: 28px 32px;">
      <h1 style="margin: 0; color: white; font-size: 20px; font-weight: 700;">&#128221; Suggest a Partner</h1>
      <p style="margin: 8px 0 0; color: rgba(255,255,255,0.8); font-size: 13px;">Opportunity: <strong>{safe_opp}</strong></p>
    </div>
    <form action="/api/suggest" method="POST" style="padding: 28px 32px;">
      <input type="hidden" name="opp_id" value="{safe_opp}">
      <input type="hidden" name="token" value="{safe_token}">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 600; color: #333;">
        Partner name you recommend:
      </label>
      <input type="text" name="partner" required placeholder="e.g. Microsoft, AWS, SAP, ServiceNow..."
             style="width: 100%; padding: 12px 16px; font-size: 15px; border: 2px solid #e0e3e8; border-radius: 8px; box-sizing: border-box; font-family: 'Ubuntu', sans-serif; outline: none; transition: border 0.2s;"
             onfocus="this.style.borderColor='#0070AD'" onblur="this.style.borderColor='#e0e3e8'">
      <label style="display: block; margin: 16px 0 6px; font-size: 14px; font-weight: 600; color: #333;">
        Why? (optional)
      </label>
      <textarea name="rationale" rows="3" placeholder="Brief reason for your suggestion..."
                style="width: 100%; padding: 12px 16px; font-size: 14px; border: 2px solid #e0e3e8; border-radius: 8px; box-sizing: border-box; font-family: 'Ubuntu', sans-serif; resize: vertical; outline: none; transition: border 0.2s;"
                onfocus="this.style.borderColor='#0070AD'" onblur="this.style.borderColor='#e0e3e8'"></textarea>
      <button type="submit"
              style="margin-top: 20px; width: 100%; padding: 14px; background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Ubuntu', sans-serif;">
        &#10004; Submit Suggestion
      </button>
    </form>
    <div style="padding: 16px 32px; background: #f8f9fb; border-top: 1px solid #eee;">
      <p style="margin: 0; font-size: 11px; color: #999;">Your suggestion will be recorded and the partner tag applied to this opportunity. THOR learns from your feedback.</p>
    </div>
  </div>
</body>
</html>"""


def handle_suggest(opp_id: str, partner: str, token: str, rationale: str = "") -> tuple[str, int]:
    """Handle a user-suggested partner submission.

    Returns:
        (html_response, status_code)
    """
    if not opp_id or not partner or not token:
        return _error_page("Missing required fields."), 400

    if not verify_token(opp_id, "", token):
        return _error_page("Invalid or expired link."), 403

    # Persist to Cosmos DB
    record_response(
        opp_id=opp_id,
        decision="suggested",
        selected_partner=partner,
    )

    # Persist to Blob Storage
    record_decision_to_blob(opp_id=opp_id, decision="suggested", partner=partner)

    # Local audit
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner=partner,
        decision="suggested",
        rationale=f"Sales Lead suggested: {rationale}" if rationale else "Sales Lead manual suggestion",
        confidence=0,
        override_partner=partner,
    )
    sync_audit_to_blob()

    safe_opp = html.escape(opp_id)
    safe_partner = html.escape(partner)
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"><title>Suggestion Recorded</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 40px 20px; background: #eef1f6; font-family: 'Ubuntu', sans-serif;">
  <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.10); text-align: center; padding: 40px;">
    <h2 style="color: #107c10; margin: 0 0 12px;">&#9989; Suggestion Recorded</h2>
    <p style="font-size: 15px; color: #333;">Partner <strong style="color: #0070AD;">{safe_partner}</strong> has been applied to opportunity <strong>{safe_opp}</strong>.</p>
    <p style="color: #666; font-size: 13px; margin-top: 20px;">Thank you — THOR learns from your feedback to improve future recommendations.</p>
    <p style="color: #999; font-size: 12px; margin-top: 24px;">You may close this window.</p>
  </div>
</body>
</html>""", 200
