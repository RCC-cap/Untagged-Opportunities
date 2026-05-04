"""Thin wrapper around Azure Cosmos DB SDK."""

from __future__ import annotations

import logging
import os
from typing import Any

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.container import ContainerProxy
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_container: ContainerProxy | None = None
_disabled: bool = False


def get_container() -> ContainerProxy | None:
    """Lazy-initialize and return the Cosmos DB container.

    Returns None if COSMOS_ENDPOINT is not configured (local/demo mode).

    Uses env vars:
        COSMOS_ENDPOINT: https://<account>.documents.azure.com:443/
        COSMOS_KEY: primary key
        COSMOS_DATABASE: database name (default: "thor")
        COSMOS_CONTAINER: container name (default: "pipeline-state")
    """
    global _container, _disabled
    if _disabled:
        return None
    if _container is not None:
        return _container

    endpoint = os.environ.get("COSMOS_ENDPOINT")
    key = os.environ.get("COSMOS_KEY")

    if not endpoint or not key:
        logger.warning("COSMOS_ENDPOINT/COSMOS_KEY not set — running without Cosmos DB (local mode)")
        _disabled = True
        return None

    database_name = os.environ.get("COSMOS_DATABASE", "thor")
    container_name = os.environ.get("COSMOS_CONTAINER", "pipeline-state")

    client = CosmosClient(endpoint, credential=key)
    database = client.create_database_if_not_exists(id=database_name)
    _container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/opp_id"),
    )
    return _container


def upsert_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Upsert a document into the container.

    The document must have 'id' and 'opp_id' fields.
    Returns empty dict if Cosmos is disabled.
    """
    container = get_container()
    if container is None:
        logger.debug(f"Cosmos disabled — skipping upsert for {doc.get('id', '?')}")
        return {}
    return container.upsert_item(body=doc)


def query_documents(
    query: str,
    parameters: list[dict[str, Any]] | None = None,
    partition_key: str | None = None,
) -> list[dict[str, Any]]:
    """Execute a parameterized SQL query.

    Args:
        query: Cosmos DB SQL query string with @param placeholders.
        parameters: List of {"name": "@param", "value": val} dicts.
        partition_key: If provided, scopes query to single partition (faster).

    Returns:
        List of matching documents. Empty list if Cosmos is disabled.
    """
    container = get_container()
    if container is None:
        return []
    kwargs: dict[str, Any] = {
        "query": query,
        "parameters": parameters or [],
        "enable_cross_partition_query": partition_key is None,
    }
    if partition_key is not None:
        kwargs["partition_key"] = partition_key

    return list(container.query_items(**kwargs))
