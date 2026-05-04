"""FastAPI webhook server for THOR partner tagging responses.

Endpoints:
    GET /api/select?opp_id=X&partner=Y&token=Z  — Partner selected
    GET /api/reject?opp_id=X&token=Z             — All rejected
    GET /health                                  — Health check
"""

from __future__ import annotations

import html
import logging

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse

from src.approval.webhook_handler import handle_reject, handle_select
from src.store.state_manager import is_responded, get_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="THOR Webhook Server",
    description="Handles Sales Lead responses to partner tag recommendations",
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Health check endpoint for Azure monitoring."""
    return {"status": "healthy", "service": "thor-webhooks"}


@app.get("/api/select", response_class=HTMLResponse)
async def select_partner(
    opp_id: str = Query(..., description="Opportunity ID"),
    partner: str = Query(..., description="Selected partner name"),
    token: str = Query(..., description="HMAC verification token"),
):
    """Handle partner selection from email button click."""
    # Idempotency: check if already responded
    if is_responded(opp_id):
        existing = get_response(opp_id)
        prev_partner = existing.get("selected_partner", "Unknown") if existing else "Unknown"
        return HTMLResponse(
            content=_already_responded_page(opp_id, prev_partner),
            status_code=200,
        )

    response_html, status_code = handle_select({
        "opp_id": opp_id,
        "partner": partner,
        "token": token,
    })
    return HTMLResponse(content=response_html, status_code=status_code)


@app.get("/api/reject", response_class=HTMLResponse)
async def reject_all(
    opp_id: str = Query(..., description="Opportunity ID"),
    token: str = Query(..., description="HMAC verification token"),
):
    """Handle reject-all from email button click."""
    # Idempotency: check if already responded
    if is_responded(opp_id):
        existing = get_response(opp_id)
        prev_partner = existing.get("selected_partner", "rejected") if existing else "rejected"
        return HTMLResponse(
            content=_already_responded_page(opp_id, prev_partner),
            status_code=200,
        )

    response_html, status_code = handle_reject({
        "opp_id": opp_id,
        "token": token,
    })
    return HTMLResponse(content=response_html, status_code=status_code)


def _already_responded_page(opp_id: str, previous_choice: str) -> str:
    """Render page when user clicks a link they already responded to."""
    safe_opp = html.escape(opp_id)
    safe_choice = html.escape(previous_choice)
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Already Responded</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #0078d4;">ℹ️ Already Responded</h2>
  <p>You have already responded to opportunity <strong>{safe_opp}</strong>.</p>
  <p>Previous selection: <strong>{safe_choice}</strong></p>
  <p style="color: #666; margin-top: 24px;">No further action needed. You may close this window.</p>
</body>
</html>"""
