"""Local snapshot storage for browser review digests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.store.cosmos_client import query_documents, upsert_document


_DIGEST_DIR = Path("data/review_digests")


def save_digest_snapshot(digest_id: str, payload: dict[str, Any]) -> Path:
    """Persist a digest snapshot to durable storage for browser rendering."""
    doc = {
        "id": f"digest-{digest_id}",
        "opp_id": f"digest:{digest_id}",
        "type": "digest_snapshot",
        "digest_id": digest_id,
        "payload": payload,
    }
    upsert_document(doc)

    _DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = _DIGEST_DIR / f"{digest_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_digest_snapshot(digest_id: str) -> dict[str, Any] | None:
    """Load a previously-saved digest snapshot."""
    docs = query_documents(
        query="SELECT * FROM c WHERE c.type = 'digest_snapshot' AND c.digest_id = @digest_id",
        parameters=[{"name": "@digest_id", "value": digest_id}],
        partition_key=f"digest:{digest_id}",
    )
    if docs:
        return docs[0].get("payload")

    path = _DIGEST_DIR / f"{digest_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))