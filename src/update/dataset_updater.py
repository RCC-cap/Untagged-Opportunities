"""Write approved partner tags back to SharePoint."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


def update_sharepoint_file(
    local_path: Path | str,
    remote_path: str | None = None,
) -> None:
    """Upload an updated file back to SharePoint via Microsoft Graph API.

    Args:
        local_path: Path to the local file to upload.
        remote_path: SharePoint path. Defaults to SHAREPOINT_FILE_PATH env var.
    """
    from src.extract.sharepoint_reader import _get_access_token, GRAPH_BASE

    token = _get_access_token()
    site_url = os.environ["SHAREPOINT_SITE_URL"]
    file_path = remote_path or os.environ["SHAREPOINT_FILE_PATH"]

    headers = {"Authorization": f"Bearer {token}"}

    # Resolve site ID
    hostname = site_url.split("//")[1].split("/")[0]
    site_path = "/".join(site_url.split("/sites/")[1:])
    site_resp = httpx.get(
        f"{GRAPH_BASE}/sites/{hostname}:/sites/{site_path}",
        headers=headers,
        timeout=30,
    )
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    # Upload file (replace existing)
    upload_url = f"{GRAPH_BASE}/sites/{site_id}/drive/root:{file_path}:/content"
    local_path = Path(local_path)

    with open(local_path, "rb") as f:
        resp = httpx.put(
            upload_url,
            headers={**headers, "Content-Type": "application/octet-stream"},
            content=f.read(),
            timeout=120,
        )
    resp.raise_for_status()
