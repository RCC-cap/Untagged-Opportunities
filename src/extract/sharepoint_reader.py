"""SharePoint file extraction via Microsoft Graph API."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_access_token() -> str:
    """Obtain an OAuth2 token using client credentials flow."""
    tenant_id = os.environ["SHAREPOINT_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.environ["SHAREPOINT_CLIENT_ID"],
        "client_secret": os.environ["SHAREPOINT_CLIENT_SECRET"],
        "scope": "https://graph.microsoft.com/.default",
    }
    resp = httpx.post(url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def download_xlsm(dest: Path | str = "data/VBA 1.xlsm") -> Path:
    """Download the .xlsm file from SharePoint to a local path.

    Returns the local Path where the file was saved.
    """
    token = _get_access_token()
    site_url = os.environ["SHAREPOINT_SITE_URL"]
    file_path = os.environ["SHAREPOINT_FILE_PATH"]

    # Resolve SharePoint site ID
    headers = {"Authorization": f"Bearer {token}"}
    hostname = site_url.split("//")[1].split("/")[0]
    site_path = "/".join(site_url.split("/sites/")[1:])
    site_resp = httpx.get(
        f"{GRAPH_BASE}/sites/{hostname}:/sites/{site_path}",
        headers=headers,
        timeout=30,
    )
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    # Download file content
    download_url = (
        f"{GRAPH_BASE}/sites/{site_id}/drive/root:{file_path}:/content"
    )
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", download_url, headers=headers, timeout=120) as stream:
        stream.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in stream.iter_bytes(chunk_size=8192):
                f.write(chunk)

    return dest
