# =========================================================
# app/api_keys.py
# =========================================================

from __future__ import annotations

import hashlib
import secrets


API_KEY_PREFIX = "ak_live_"


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.

    The plaintext key must only be shown to the caller once.
    Do not write the plaintext key to logs or audit events.
    """
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def fingerprint_api_key(api_key: str) -> str:
    """
    Return a non-reversible fingerprint suitable for audit/storage.
    """
    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()[:16]


def is_api_key_request(query: str) -> bool:
    """
    Detect an explicit API-key generation request.
    """
    normalized = " ".join(query.lower().split())

    patterns = (
        "generate api key",
        "create api key",
        "make api key",
        "new api key",
        "generate an api key",
        "create an api key",
        "make an api key",
        "new api key",
    )

    return any(
        pattern in normalized
        for pattern in patterns
    )
