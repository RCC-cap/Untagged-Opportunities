"""Azure Blob Storage file extraction."""

from __future__ import annotations

import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()


def download_from_blob(
    container_name: str | None = None,
    blob_name: str | None = None,
    dest: Path | str = "data/VBA 1.xlsm",
) -> Path:
    """Download a file from Azure Blob Storage.

    Args:
        container_name: Blob container name. Defaults to BLOB_CONTAINER_NAME env var.
        blob_name: Blob file name. Defaults to BLOB_FILE_NAME env var.
        dest: Local destination path.

    Returns:
        Path to the downloaded file.
    """
    connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = container_name or os.environ["BLOB_CONTAINER_NAME"]
    blob_name = blob_name or os.environ["BLOB_FILE_NAME"]

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)

    with open(dest, "wb") as f:
        stream = blob_client.download_blob()
        stream.readinto(f)

    return dest
