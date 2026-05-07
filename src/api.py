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

from src.approval.browser_review import render_review_page
from src.approval.webhook_handler import handle_reject, handle_select
from src.approval.token_utils import verify_digest_token, verify_token
from src.extract.blob_writer import record_decision_to_blob, sync_audit_to_blob
from src.store.digest_store import load_digest_snapshot
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


@app.get("/review", response_class=HTMLResponse)
async def browser_review(
    digest_id: str = Query(..., description="Digest snapshot ID"),
    token: str = Query(..., description="Digest access token"),
):
    """Render a browser-first review workspace for one digest."""
    if not verify_digest_token(digest_id, token):
        return HTMLResponse(content=_error_page("Invalid or expired review link."), status_code=403)

    digest = load_digest_snapshot(digest_id)
    if not digest:
        return HTMLResponse(content=_error_page("Review page not found or no longer available."), status_code=404)

    for opp in digest.get("opportunities", []):
        response = get_response(opp["opp_id"])
        if response:
            opp["response"] = response

    logger.info("Browser digest opened: %s (%s opps)", digest_id, len(digest.get("opportunities", [])))
    append_audit_entry(
        opportunity_id=f"digest:{digest_id}",
        recommended_partner="",
        decision="digest_opened",
        rationale=f"Browser review opened for {digest.get('lead_email', 'unknown lead')}",
        confidence=0,
    )
    sync_audit_to_blob()

    return HTMLResponse(content=render_review_page(digest), status_code=200)


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
  <meta charset="utf-8"><title>Suggest Partner — THOR</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:40px 20px;background:#eef1f6;font-family:'Ubuntu','Segoe UI',sans-serif;">
  <div style="max-width:520px;margin:0 auto;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.10);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#0070AD 0%,#12ABDB 100%);padding:28px 32px;">
      <h1 style="margin:0;color:white;font-size:20px;font-weight:700;">&#128221; Suggest a Partner</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Opportunity: <strong>{safe_opp}</strong></p>
    </div>
    <form method="POST" action="/api/suggest" style="padding:28px 32px;">
      <input type="hidden" name="opp_id" value="{safe_opp}" />
      <input type="hidden" name="token" value="{safe_token}" />
      <label style="display:block;margin-bottom:6px;font-size:14px;font-weight:600;color:#333;">Partner Name</label>
      <input type="text" name="partner" placeholder="e.g. Microsoft, AWS, SAP, ServiceNow..." required
             style="width:100%;padding:12px 16px;font-size:15px;border:2px solid #e0e3e8;border-radius:8px;box-sizing:border-box;font-family:'Ubuntu',sans-serif;outline:none;"
             onfocus="this.style.borderColor='#0070AD'" onblur="this.style.borderColor='#e0e3e8'" />
      <p style="font-size:12px;color:#888;margin:6px 0 0;">Type the partner that should be tagged for this opportunity.</p>
      <button type="submit"
              style="margin-top:20px;width:100%;padding:14px;background:linear-gradient(135deg,#0070AD 0%,#12ABDB 100%);color:white;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;font-family:'Ubuntu',sans-serif;">
        &#10004; Submit Suggestion
      </button>
    </form>
    <div style="padding:16px 32px;background:#f8f9fb;border-top:1px solid #eee;">
      <p style="margin:0;font-size:11px;color:#999;">Your suggestion will be recorded. THOR learns from your feedback.</p>
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
  <meta charset="utf-8"><title>Suggestion Recorded — THOR</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body style="font-family:'Ubuntu',sans-serif;background:#eef1f6;margin:0;padding:40px 20px;text-align:center;">
  <div style="max-width:480px;margin:0 auto;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.10);padding:40px 32px;">
    <h2 style="color:#107c10;font-size:22px;">&#9989; Suggestion Recorded</h2>
    <p style="color:#444;font-size:15px;line-height:1.6;">Partner <span style="display:inline-block;background:#e6f4ea;color:#1e7e34;padding:6px 16px;border-radius:10px;font-size:15px;font-weight:700;">{safe_partner}</span> has been recorded for opportunity <strong>{safe_opp}</strong>.</p>
    <p style="color:#888;margin-top:24px;font-size:13px;">Thank you — THOR learns from your feedback.<br>You may close this window.</p>
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


@app.get("/api/comment", response_class=HTMLResponse)
async def comment_form(
    opp_id: str = Query(..., description="Opportunity ID"),
    token: str = Query(..., description="HMAC verification token"),
):
    """Render a form where the Sales Lead can leave a comment."""
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
  <meta charset="utf-8"><title>Add Comment — THOR</title>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:40px 20px;background:#eef1f6;font-family:'Ubuntu','Segoe UI',sans-serif;">
  <div style="max-width:520px;margin:0 auto;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.10);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#0070AD 0%,#12ABDB 100%);padding:28px 32px;">
      <h1 style="margin:0;color:white;font-size:20px;font-weight:700;">&#128172; Add a Comment</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Opportunity: <strong>{safe_opp}</strong></p>
    </div>
    <form method="POST" action="/api/comment" style="padding:28px 32px;">
      <input type="hidden" name="opp_id" value="{safe_opp}" />
      <input type="hidden" name="token" value="{safe_token}" />
      <label style="display:block;margin-bottom:6px;font-size:14px;font-weight:600;color:#333;">Your Comment</label>
      <textarea name="comment" rows="4" required placeholder="e.g. This deal is internal only, not relevant for partners..."
                style="width:100%;padding:12px 16px;font-size:14px;border:2px solid #e0e3e8;border-radius:8px;box-sizing:border-box;font-family:'Ubuntu',sans-serif;resize:vertical;outline:none;"
                onfocus="this.style.borderColor='#0070AD'" onblur="this.style.borderColor='#e0e3e8'"></textarea>
      <button type="submit"
              style="margin-top:20px;width:100%;padding:14px;background:linear-gradient(135deg,#0070AD 0%,#12ABDB 100%);color:white;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;font-family:'Ubuntu',sans-serif;">
        &#10004; Submit Comment
      </button>
    </form>
  </div>
</body>
</html>""", status_code=200)


@app.post("/api/comment", response_class=HTMLResponse)
async def comment_submit(
    opp_id: str = Form(...),
    comment: str = Form(...),
    token: str = Form(...),
):
    """Process comment form submission."""
    if is_responded(opp_id):
        existing = get_response(opp_id)
        prev_partner = existing.get("selected_partner", "Unknown") if existing else "Unknown"
        return HTMLResponse(content=_already_responded_page(opp_id, prev_partner), status_code=200)

    if not verify_token(opp_id, "", token):
        return HTMLResponse(content=_error_page("Invalid or expired link."), status_code=403)

    comment = comment.strip()[:500]
    if not comment:
        return HTMLResponse(content=_error_page("Comment cannot be empty."), status_code=400)

    record_response(opp_id=opp_id, decision="commented", selected_partner=None, comment=comment)

    append_audit_entry(
        opportunity_id=opp_id,
        recommended_partner="",
        decision="commented",
        rationale=f"Sales Lead comment: {comment}",
        confidence=0,
    )

    record_decision_to_blob(opp_id=opp_id, decision="commented", partner=None, comment=comment)
    sync_audit_to_blob()

    safe_opp = html.escape(opp_id)
    safe_comment = html.escape(comment[:100])
    return HTMLResponse(content=f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Comment Saved — THOR</title></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:500px;margin:60px auto;text-align:center;">
  <h2 style="color:#107c10;">&#9989; Comment Saved</h2>
  <p>Your comment for opportunity <strong>{safe_opp}</strong> has been recorded.</p>
  <p style="color:#666;background:#f8f9fb;padding:12px 16px;border-radius:8px;font-style:italic;">"{safe_comment}"</p>
  <p style="color:#888;margin-top:24px;font-size:13px;">Thank you — you may close this window.</p>
</body>
</html>""", status_code=200)


def _error_page(message: str) -> str:
    """Render error page."""
    safe_msg = html.escape(message)
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error — THOR</title></head>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 500px; margin: 60px auto; text-align: center;">
  <h2 style="color: #d83b01;">⚠️ Error</h2>
  <p>{safe_msg}</p>
</body>
</html>"""
