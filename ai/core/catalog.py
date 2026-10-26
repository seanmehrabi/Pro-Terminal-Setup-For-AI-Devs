"""Load and merge application catalog YAML."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from ai.core.yaml_lite import YamlLiteError, parse


def load_catalog(root: str) -> Dict[str, Any]:
    """Load base catalog and merge optional per-platform source overlays."""
    catalog_dir = os.path.join(root, "ai", "catalog")
    apps_path = os.path.join(catalog_dir, "applications.yaml")
    profiles_path = os.path.join(catalog_dir, "profiles.yaml")

    apps_doc = _read_yaml(apps_path)
    profiles_doc = _read_yaml(profiles_path)

    applications: List[Dict[str, Any]] = list(apps_doc.get("applications") or [])
    profiles = _normalize_profiles(profiles_doc)

    by_id: Dict[str, Dict[str, Any]] = {}
    for app in applications:
        app_id = app.get("id")
        if app_id:
            by_id[str(app_id)] = app

    sources_dir = os.path.join(catalog_dir, "sources")
    for platform_name, filename in (
        ("macos", "macos.yaml"),
        ("windows", "windows.yaml"),
        ("linux", "linux.yaml"),
    ):
        path = os.path.join(sources_dir, filename)
        if not os.path.isfile(path):
            continue
        overlay = _read_yaml(path)
        if not isinstance(overlay, dict):
            continue
        for app_id, platform_cfg in overlay.items():
            if not isinstance(platform_cfg, dict):
                continue
            app = by_id.get(str(app_id))
            if app is None:
                continue
            platforms = app.setdefault("platforms", {})
            if not isinstance(platforms, dict):
                platforms = {}
                app["platforms"] = platforms
            merged = dict(platforms.get(platform_name) or {})
            merged.update(platform_cfg)
            platforms[platform_name] = merged

    return {"applications": applications, "profiles": profiles}


def _read_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        return parse(text)
    except YamlLiteError as exc:
        raise YamlLiteError("{}: {}".format(path, exc)) from exc


def _normalize_profiles(doc: Any) -> Dict[str, List[str]]:
    if not isinstance(doc, dict):
        return {}
    raw = doc.get("profiles", doc)
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for name, value in raw.items():
        if isinstance(value, list):
            out[str(name)] = [str(x) for x in value]
        elif isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            out[str(name)] = parts
        else:
            out[str(name)] = []
    return out
