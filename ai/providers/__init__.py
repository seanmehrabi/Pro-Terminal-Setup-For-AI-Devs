"""AI provider metadata, preferences, credentials, and status."""

from __future__ import annotations

from ai.providers.config import (
    ALLOWED_PREF_KEYS,
    DEFAULT_CONFIG_PATH,
    load_preferences,
    set_preferences,
)
from ai.providers.credentials import delete_secret, get_secret, set_secret
from ai.providers.registry import get_provider, list_providers
from ai.providers.provider_status import status

__all__ = [
    "ALLOWED_PREF_KEYS",
    "DEFAULT_CONFIG_PATH",
    "delete_secret",
    "get_provider",
    "get_secret",
    "list_providers",
    "load_preferences",
    "set_preferences",
    "set_secret",
    "status",
]
