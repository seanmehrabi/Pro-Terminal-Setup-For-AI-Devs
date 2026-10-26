"""Non-secret provider preferences persisted as JSON."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Set

from ai.providers.registry import get_provider

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.expanduser("~"),
    ".config",
    "pro-terminal-setup",
    "ai-config.json",
)

ALLOWED_PREF_KEYS: Set[str] = {"base_url", "enabled", "default_model", "notes"}

SECRET_LIKE_KEYS: Set[str] = {
    "api_key",
    "token",
    "secret",
    "password",
    "credentials",
    "github_token",
    "access_token",
}


def _empty_config() -> Dict[str, Any]:
    return {"providers": {}}


def load_preferences(path: Optional[str] = None) -> Dict[str, Any]:
    """Load non-secret preferences from JSON. Missing file yields empty providers map."""
    config_path = path if path is not None else DEFAULT_CONFIG_PATH
    if not os.path.isfile(config_path):
        return _empty_config()
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return _empty_config()
    if not isinstance(data, dict):
        return _empty_config()
    providers = data.get("providers")
    if not isinstance(providers, dict):
        data["providers"] = {}
    return data


def _sanitize_prefs(prefs: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in prefs.items():
        if key in SECRET_LIKE_KEYS:
            raise ValueError("secret values must not be stored in ai-config.json")
        if key not in ALLOWED_PREF_KEYS:
            continue
        cleaned[key] = value
    return cleaned


def set_preferences(
    provider: str,
    prefs: Dict[str, Any],
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Merge non-secret preferences for one provider and write JSON."""
    if get_provider(provider) is None:
        return {"ok": False, "detail": "unknown provider: {}".format(provider)}
    if not isinstance(prefs, dict):
        return {"ok": False, "detail": "preferences must be a mapping"}

    try:
        sanitized = _sanitize_prefs(prefs)
    except ValueError as exc:
        return {"ok": False, "detail": str(exc)}

    config_path = path if path is not None else DEFAULT_CONFIG_PATH
    data = load_preferences(config_path)
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers

    existing = providers.get(provider)
    if not isinstance(existing, dict):
        existing = {}
    merged = dict(existing)
    merged.update(sanitized)
    providers[provider] = merged

    parent = os.path.dirname(config_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        return {"ok": False, "detail": "failed to write config: {}".format(exc)}

    return {"ok": True, "detail": "saved", "provider": provider}


def provider_preferences(provider: str, path: Optional[str] = None) -> Dict[str, Any]:
    """Return stored preferences for a provider (may be empty)."""
    data = load_preferences(path)
    providers = data.get("providers") or {}
    entry = providers.get(provider)
    if isinstance(entry, dict):
        return dict(entry)
    return {}
