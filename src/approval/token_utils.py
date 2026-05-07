"""HMAC token utilities for secure webhook links."""

from __future__ import annotations

import hashlib
import hmac
import os
import time


def _get_secret() -> bytes:
    """Get the HMAC secret from environment."""
    secret = os.environ.get("WEBHOOK_HMAC_SECRET", "")
    if not secret:
        raise ValueError("WEBHOOK_HMAC_SECRET environment variable not set")
    return secret.encode()


def generate_token(opp_id: str, partner: str = "", ttl_hours: int = 168) -> str:
    """Generate an HMAC-signed token for a webhook URL.

    Token encodes: opp_id + partner + expiry timestamp.
    Default TTL is 7 days (168 hours).

    Args:
        opp_id: Opportunity ID to embed in token.
        partner: Partner name (can be empty for reject-all links).
        ttl_hours: Token validity in hours.

    Returns:
        Token string: "{expiry_ts}.{hex_signature}"
    """
    secret = _get_secret()
    expiry = int(time.time()) + (ttl_hours * 3600)
    message = f"{opp_id}:{partner}:{expiry}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return f"{expiry}.{signature}"


def generate_digest_token(digest_id: str, ttl_hours: int = 168) -> str:
    """Generate an HMAC-signed token for a browser review digest."""
    secret = _get_secret()
    expiry = int(time.time()) + (ttl_hours * 3600)
    message = f"digest:{digest_id}:{expiry}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return f"{expiry}.{signature}"


def verify_token(opp_id: str, partner: str, token: str) -> bool:
    """Verify an HMAC token from a webhook callback.

    Checks both signature validity and expiry.

    Args:
        opp_id: Opportunity ID from the URL.
        partner: Partner name from the URL (empty string for reject).
        token: Token string from the URL.

    Returns:
        True if token is valid and not expired.
    """
    try:
        secret = _get_secret()
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False

        expiry_str, provided_sig = parts
        expiry = int(expiry_str)

        # Check expiry
        if time.time() > expiry:
            return False

        # Recompute signature
        message = f"{opp_id}:{partner}:{expiry}".encode()
        expected_sig = hmac.new(secret, message, hashlib.sha256).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(provided_sig, expected_sig)
    except (ValueError, TypeError):
        return False


def verify_digest_token(digest_id: str, token: str) -> bool:
    """Verify a browser review digest token."""
    try:
        secret = _get_secret()
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False

        expiry_str, provided_sig = parts
        expiry = int(expiry_str)
        if time.time() > expiry:
            return False

        message = f"digest:{digest_id}:{expiry}".encode()
        expected_sig = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided_sig, expected_sig)
    except (ValueError, TypeError):
        return False
