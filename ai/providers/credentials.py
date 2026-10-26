"""Credential storage via ai.security.store (never written to JSON config)."""

from __future__ import annotations

from typing import Any, Dict, Optional

_STORE_UNAVAILABLE = {"ok": False, "detail": "credential store unavailable"}


def _get_store() -> Any:
    try:
        from ai.security import store  # type: ignore
    except ImportError:
        return None
    return store


def set_secret(provider: str, name: str, value: str) -> Dict[str, Any]:
    store = _get_store()
    if store is None:
        return dict(_STORE_UNAVAILABLE)
    try:
        result = store.set_secret(provider, name, value)
    except Exception as exc:  # noqa: BLE001 — surface store failures
        return {"ok": False, "detail": str(exc)}
    if isinstance(result, dict):
        return result
    return {"ok": True, "detail": "stored"}


def get_secret(provider: str, name: str) -> Dict[str, Any]:
    store = _get_store()
    if store is None:
        return dict(_STORE_UNAVAILABLE)
    try:
        result = store.get_secret(provider, name)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)}
    if isinstance(result, dict):
        return result
    if result:
        return {"ok": True, "value": result}
    return {"ok": False, "detail": "not found"}


def delete_secret(provider: str, name: str) -> Dict[str, Any]:
    store = _get_store()
    if store is None:
        return dict(_STORE_UNAVAILABLE)
    try:
        result = store.delete_secret(provider, name)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)}
    if isinstance(result, dict):
        return result
    return {"ok": True, "detail": "deleted"}
