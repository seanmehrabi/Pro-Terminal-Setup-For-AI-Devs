"""Provider readiness: credential configuration or local reachability."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai.providers.config import provider_preferences
from ai.providers.credentials import get_secret
from ai.providers.registry import get_provider
from ai.providers.reachability import tcp_reachable


def _cloud_configured(provider_id: str, meta: Dict[str, Any]) -> bool:
    names = meta.get("secret_names") or []
    if not names:
        return False
    for name in names:
        result = get_secret(provider_id, name)
        if not result.get("ok"):
            continue
        value = result.get("value")
        if value:
            return True
    return False


def status(provider: str, path: Optional[str] = None) -> Dict[str, Any]:
    """Report whether a cloud provider is configured or a local server is reachable."""
    meta = get_provider(provider)
    if meta is None:
        return {"ok": False, "detail": "unknown provider: {}".format(provider)}

    prefs = provider_preferences(provider, path)
    base_url = prefs.get("base_url") or meta.get("default_base_url") or ""

    payload: Dict[str, Any] = {
        "ok": True,
        "provider": provider,
        "kind": meta.get("kind"),
        "base_url": base_url,
    }

    if meta.get("kind") == "local":
        payload["reachable"] = tcp_reachable(base_url)
    else:
        payload["configured"] = _cloud_configured(provider, meta)

    return payload
