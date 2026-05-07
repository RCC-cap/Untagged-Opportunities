"""Azure Blob Storage write-back for persisting results and audit logs."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RESULTS_BLOB = "thor-results/decisions.jsonl"
AUDIT_BLOB = "thor-results/audit_log.jsonl"


def _get_blob_service() -> BlobServiceClient | None:
    """Get BlobServiceClient or None if not configured."""
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — blob write disabled")
        return None
    return BlobServiceClient.from_connection_string(conn_str)


def _get_container_name() -> str:
    return os.environ.get("BLOB_CONTAINER_NAME", "thor-data")


def append_to_blob(blob_name: str, line: str) -> bool:
    """Append a single JSON line to a blob (append blob).

    Creates the blob if it doesn't exist.

    Returns:
        True if successful, False if blob storage not available.
    """
    service = _get_blob_service()
    if not service:
        return False

    container_name = _get_container_name()
    container_client = service.get_container_client(container_name)

    # Ensure container exists
    try:
        container_client.get_container_properties()
    except Exception:
        container_client.create_container()

    blob_client = container_client.get_blob_client(blob_name)

    # Try to append; if blob doesn't exist, create it first
    data = (line.rstrip("\n") + "\n").encode("utf-8")
    try:
        blob_client.get_blob_properties()
        # Blob exists — download, append, re-upload (block blob approach)
        existing = blob_client.download_blob().readall()
        blob_client.upload_blob(existing + data, overwrite=True)
    except Exception:
        # Blob doesn't exist — create it
        blob_client.upload_blob(data, overwrite=True)

    return True


def record_decision_to_blob(
    opp_id: str,
    decision: str,
    partner: str | None = None,
    suggested_by: str | None = None,
    comment: str | None = None,
) -> bool:
    """Write a partner decision to Blob Storage (persistent history).

    Args:
        opp_id: Opportunity ID.
        decision: "selected" | "rejected" | "suggested" | "commented".
        partner: Chosen or suggested partner name.
        suggested_by: Email of who suggested (for suggest flow).
        comment: Optional comment from Sales Lead.

    Returns:
        True if written successfully.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "opp_id": opp_id,
        "decision": decision,
        "partner": partner,
        "suggested_by": suggested_by,
    }
    if comment:
        entry["comment"] = comment
    line = json.dumps(entry, ensure_ascii=False)
    success = append_to_blob(RESULTS_BLOB, line)
    if success:
        logger.info(f"Blob write-back: {opp_id} → {decision} ({partner})")
    return success


def sync_audit_to_blob(local_path: str = "data/audit_log.jsonl") -> bool:
    """Upload the full local audit log to Blob Storage.

    Called after each audit entry to ensure persistence across redeploys.

    Returns:
        True if uploaded successfully.
    """
    service = _get_blob_service()
    if not service:
        return False

    path = Path(local_path)
    if not path.exists():
        return False

    container_name = _get_container_name()
    blob_client = service.get_blob_client(container=container_name, blob=AUDIT_BLOB)

    with open(path, "rb") as f:
        blob_client.upload_blob(f.read(), overwrite=True)

    logger.info(f"Audit log synced to blob: {AUDIT_BLOB}")
    return True


def get_all_decisions() -> list[dict]:
    """Read all decisions from Blob Storage.

    Returns:
        List of decision records, or empty list if unavailable.
    """
    service = _get_blob_service()
    if not service:
        return []

    container_name = _get_container_name()
    blob_client = service.get_blob_client(container=container_name, blob=RESULTS_BLOB)

    try:
        data = blob_client.download_blob().readall().decode("utf-8")
        return [json.loads(line) for line in data.strip().split("\n") if line.strip()]
    except Exception:
        return []


def get_decided_opp_ids() -> set[str]:
    """Return set of opp IDs that have a decision in Blob (for dedup)."""
    decisions = get_all_decisions()
    return {d["opp_id"] for d in decisions}
