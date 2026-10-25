"""Adapter protocol and dynamic loader with unsupported stub."""

from __future__ import annotations

import importlib
import types
from typing import Any, Dict


# Protocol (each platform module should implement):
#
# detect(app: dict, host: dict) -> dict
#   Keys: installed (bool), version (str), path (str), method (str)
#
# install(app: dict, host: dict, dry_run: bool) -> dict
# update(app: dict, host: dict, dry_run: bool) -> dict
# uninstall(app: dict, host: dict, dry_run: bool) -> dict
# repair(app: dict, host: dict, dry_run: bool) -> dict
#
# Result keys: ok (bool), action (str), detail (str), skipped (bool)


def _unsupported_result(action: str = "unsupported") -> Dict[str, Any]:
    return {
        "ok": False,
        "action": action,
        "detail": "adapter not implemented",
        "skipped": True,
        "installed": False,
    }


def _stub_detect(app: Dict[str, Any], host: Dict[str, Any]) -> Dict[str, Any]:
    return {"installed": False, "version": "", "path": "", "method": ""}


def _make_stub_module() -> types.ModuleType:
    mod = types.ModuleType("ai.adapters.stub")

    def _op(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        return _unsupported_result()

    mod.detect = _stub_detect  # type: ignore[attr-defined]
    mod.install = _op  # type: ignore[attr-defined]
    mod.update = _op  # type: ignore[attr-defined]
    mod.uninstall = _op  # type: ignore[attr-defined]
    mod.repair = _op  # type: ignore[attr-defined]
    return mod


_STUB = _make_stub_module()


def get_adapter(host: Dict[str, Any]) -> types.ModuleType:
    """Return the platform adapter module for host['os'], or an unsupported stub."""
    os_name = host.get("os", "other")
    module_name = {
        "macos": "ai.adapters.macos",
        "windows": "ai.adapters.windows",
        "linux": "ai.adapters.linux",
    }.get(os_name)
    if not module_name:
        return _STUB
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return _STUB
