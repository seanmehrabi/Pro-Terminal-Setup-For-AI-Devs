"""OS-backed secret storage (never plaintext in repo or config)."""

from __future__ import annotations

from ai.security.store import (
    backend_name,
    delete_secret,
    get_secret,
    redact,
    set_secret,
)

__all__ = [
    "backend_name",
    "delete_secret",
    "get_secret",
    "redact",
    "set_secret",
]
