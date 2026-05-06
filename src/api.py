"""FastAPI webhook server for THOR partner tagging responses.

Endpoints:
    GET  /api/select?opp_id=X&partner=Y&token=Z  — Partner selected
    GET  /api/reject?opp_id=X&token=Z             — All rejected
    POST /api/run                                 — Trigger pipeline run
    GET  /health                                  — Health check
"""

from __future__ import annotations

import html
import logging
import traceback

from fastapi import FastAPI, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.approval.webhook_handler import handle_reject, handle_select
from src.approval.token_utils import verify_token
from src.extract.blob_writer import record_decision_to_blob, sync_audit_to_blob
from src.store.state_manager import is_responded, get_response, record_response
from src.audit.audit_logger import append_audit_entry

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


class RunRequest(BaseModel):
    """Optional parameters for triggering a pipeline run."""
    file: str | None = None
    dry_run: bool = False
    use_llm: bool = True


@app.post("/api/run")
async def run_pipeline_endpoint(body: RunRequest | None = None):
    """Trigger a full pipeline run and return JSON summary.

    Called by n8n HTTP Request node instead of Execute Command.
    """
    from pathlib import Path
    from src.main import run_pipeline

    params = body or RunRequest()
    file_path = Path(params.file) if params.file else None

    try:
        result = run_pipeline(
            file_path=file_path,
            dry_run=params.dry_run,
            use_llm=params.use_llm,
        )
        return JSONResponse(content=result, status_code=200)
    except Exception:
        logger.exception("Pipeline run failed")
        return JSONResponse(
            content={"error": traceback.format_exc()},
            status_code=500,
        )


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


@app.get("/api/suggest", response_class=HTMLResponse)
async def suggest_form(
    opp_id: str = Query(..., description="Opportunity ID"),
    token: str = Query(..., description="HMAC verification token"),
):
    """Render a form where the Sales Lead can suggest a different partner."""
    if is_responded(opp_id):
        existing = get_response(opp_id)
        prev_partner = existing.get("selected_partner", "Unknown") if existing else "Unknown"
        return HTMLResponse(content=_already_responded_page(opp_id, prev_partner), status_code=200)

    if not verify_token(opp_id, "", token):
        return HTMLResponse(content=_error_page("Invalid or expired link."), status_code=403)

    safe_opp = html.escape(opp_id)
    safe_token = html.escape(token)
    return HTMLResponse(content=f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"><title>Suggest Partner — UOA</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Ubuntu', sans-serif; background: #eef1f6; margin: 0; padding: 40px 20px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.10); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #0070AD 0%, #12ABDB 60%, #2EDAA8 100%); padding: 28px 32px; color: white; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0; opacity: 0.8; font-size: 13px; }}
    .body {{ padding: 28px 32px; }}
    .body label {{ display: block; font-size: 14px; font-weight: 600; color: #333; margin-bottom: 8px; }}
    .body input[type=text] {{ width: 100%; padding: 12px 16px; border: 2px solid #e0e3e8; border-radius: 10px; font-size: 15px; font-family: 'Ubuntu', sans-serif; box-sizing: border-box; transition: border-color 0.2s; }}
    .body input[type=text]:focus {{ outline: none; border-color: #0070AD; }}
    .body .help {{ font-size: 12px; color: #888; margin-top: 6px; }}
    .body button {{ margin-top: 20px; background: linear-gradient(135deg, #0070AD 0%, #12ABDB 100%); color: white; border: none; padding: 14px 32px; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Ubuntu', sans-serif; }}
    .body button:hover {{ opacity: 0.9; }}
    .opp-id {{ display: inline-block; background: #f0f7ff; color: #0070AD; padding: 4px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>&#128221; Suggest a Different Partner</h1>
      <p>None of UOA's recommendations fit? Tell us the correct partner.</p>
    </div>
    <div class="body">
      <span class="opp-id">Opportunity: {safe_opp}</span>
      <form method="POST" action="/api/suggest">
        <input type="hidden" name="opp_id" value="{safe_opp}" />
        <input type="hidden" name="token" value="{safe_token}" />
        <label for="partner">Partner Name</label>
        <input type="text" id="partner" name="partner" placeholder="e.g. Microsoft, AWS, SAP, ServiceNow..." required />
        <p class="help">Type the partner that should be tagged for this opportunity.</p>
        <button type="submit">&#10004; Submit Suggestion</button>
      </form>
    </div>
  </div>
</body>
</html>""", status_code=200)


@app.post("/api/suggest", response_class=HTMLResponse)
async def suggest_submit(
    opp_id: str = Form(...),
    partner: str = Form(...),
    token: str = Form(...),
):
    """Process partner suggestion form submission."""
    if is_responded(opp_id):
        existing = get_response(opp_id)
        prev_partner = existing.get("selected_partner", "Unknown") if existing else "Unknown"
        return HTMLResponse(content=_already_responded_page(opp_id, prev_partner), status_code=200)

    if not verify_token(opp_id, "", token):
        return HTMLResponse(content=_error_page("Invalid or expired link."), status_code=403)

    # Sanitize partner input
    partner = partner.strip()[:100]
    if not partner:
        return HTMLResponse(content=_error_page("Partner name cannot be empty."), status_code=400)

    # Record in state manager (Cosmos DB / local)
    record_response(opp_id=opp_id, decision="suggested", selected_partner=partner)

    # Audit log
    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner=partner,
        decision="suggested",
        rationale=f"Sales Lead manually suggested '{partner}' (AI recommendations rejected)",
        confidence=0,
    )

    # Persist to Blob
    record_decision_to_blob(opp_id=opp_id, decision="suggested", partner=partner)
    sync_audit_to_blob()

    safe_opp = html.escape(opp_id)
    safe_partner = html.escape(partner)
    return HTMLResponse(content=f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"><title>Suggestion Recorded — UOA</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Ubuntu', sans-serif; background: #eef1f6; margin: 0; padding: 40px 20px; text-align: center; }}
    .card {{ max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.10); padding: 40px 32px; }}
    h2 {{ color: #107c10; font-size: 22px; }}
    p {{ color: #444; font-size: 15px; line-height: 1.6; }}
    .tag {{ display: inline-block; background: #e6f4ea; color: #1e7e34; padding: 6px 16px; border-radius: 10px; font-size: 15px; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>&#9989; Suggestion Recorded</h2>
    <p>Partner <span class="tag">{safe_partner}</span> has been recorded for opportunity <strong>{safe_opp}</strong>.</p>
    <p style="color: #888; margin-top: 24px; font-size: 13px;">Thank you for your feedback — this helps UOA learn and improve.<br>You may close this window.</p>
  </div>
</body>
</html>""", status_code=200)


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
