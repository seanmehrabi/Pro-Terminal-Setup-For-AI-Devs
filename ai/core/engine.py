"""Plan selection, build, and execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ai.adapters.base import get_adapter


def select_ids(
    catalog: Dict[str, Any],
    profile: Optional[Sequence[str]],
    all_apps: bool,
    explicit_ids: Optional[Sequence[str]],
) -> List[str]:
    """Resolve application ids from profiles, --all, or explicit list."""
    profiles_map: Dict[str, List[str]] = catalog.get("profiles") or {}
    apps: List[Dict[str, Any]] = catalog.get("applications") or []
    known = {str(a.get("id")) for a in apps if a.get("id")}

    chosen: List[str] = []
    seen = set()

    def add_many(ids: Sequence[str]) -> None:
        for app_id in ids:
            sid = str(app_id)
            if sid in known and sid not in seen:
                seen.add(sid)
                chosen.append(sid)

    if explicit_ids:
        add_many(explicit_ids)
    if profile:
        for name in profile:
            add_many(profiles_map.get(name, []))
    if all_apps:
        add_many(sorted(known))

    return chosen


def _app_by_id(catalog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for app in catalog.get("applications") or []:
        app_id = app.get("id")
        if app_id:
            out[str(app_id)] = app
    return out


def _platform_entry(app: Dict[str, Any], host: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    platforms = app.get("platforms") or {}
    if not isinstance(platforms, dict):
        return None
    entry = platforms.get(host.get("os", ""))
    if isinstance(entry, dict):
        return entry
    return None


def build_plan(catalog: Dict[str, Any], host: Dict[str, Any], ids: List[str]) -> List[Dict[str, Any]]:
    """Build install/skip/manual plan entries for the given application ids."""
    by_id = _app_by_id(catalog)
    adapter = get_adapter(host)
    plan: List[Dict[str, Any]] = []

    for app_id in ids:
        app = by_id.get(app_id)
        if app is None:
            plan.append(
                {
                    "id": app_id,
                    "name": app_id,
                    "action": "unsupported",
                    "detail": "unknown application id",
                }
            )
            continue

        name = str(app.get("name") or app_id)
        entry = _platform_entry(app, host)
        if entry is None:
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "unsupported",
                    "detail": "no platform definition for {}".format(host.get("os")),
                }
            )
            continue

        method = str(entry.get("method") or "").strip()
        verified = entry.get("verified", False)
        fallback_method = str(entry.get("fallback_method") or "").strip()

        if method == "pending" or not method:
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "unsupported",
                    "detail": "installation method pending",
                }
            )
            continue

        if not verified:
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "manual",
                    "detail": "not verified for automated install; see official_url",
                }
            )
            continue

        if method == "manual" and fallback_method:
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "fallback",
                    "detail": "primary manual; fallback: {}".format(fallback_method),
                }
            )
            continue

        if method == "manual":
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "manual",
                    "detail": "manual installation required",
                }
            )
            continue

        detect_info = adapter.detect(app, host)
        if detect_info.get("installed"):
            plan.append(
                {
                    "id": app_id,
                    "name": name,
                    "action": "skip",
                    "detail": "already installed",
                    "version": detect_info.get("version") or "",
                }
            )
            continue

        plan.append(
            {
                "id": app_id,
                "name": name,
                "action": "install",
                "detail": "via {}".format(method),
            }
        )

    return plan


def run_plan(
    plan: List[Dict[str, Any]],
    host: Dict[str, Any],
    catalog: Dict[str, Any],
    dry_run: bool,
    operation: str = "install",
) -> List[Dict[str, Any]]:
    """Execute plan steps through the platform adapter."""
    by_id = _app_by_id(catalog)
    adapter = get_adapter(host)
    op_fn = {
        "install": adapter.install,
        "update": adapter.update,
        "uninstall": adapter.uninstall,
        "repair": adapter.repair,
    }.get(operation, adapter.install)

    results: List[Dict[str, Any]] = []
    for step in plan:
        app_id = step.get("id")
        action = step.get("action")
        base = {
            "id": app_id,
            "name": step.get("name"),
            "planned_action": action,
        }

        if action in ("skip", "unsupported", "manual"):
            results.append(
                {
                    **base,
                    "ok": action == "skip",
                    "action": action,
                    "detail": step.get("detail", ""),
                    "skipped": True,
                }
            )
            continue

        if action == "fallback":
            results.append(
                {
                    **base,
                    "ok": False,
                    "action": "fallback",
                    "detail": step.get("detail", ""),
                    "skipped": not dry_run,
                }
            )
            continue

        app = by_id.get(str(app_id), {})
        if dry_run and operation == "install":
            results.append(
                {
                    **base,
                    "ok": True,
                    "action": "dry-run",
                    "detail": "would {} {}".format(operation, app_id),
                    "skipped": False,
                }
            )
            continue

        if dry_run:
            results.append(
                {
                    **base,
                    "ok": True,
                    "action": "dry-run",
                    "detail": "would {} {}".format(operation, app_id),
                    "skipped": False,
                }
            )
            continue

        outcome = op_fn(app, host, dry_run)
        results.append({**base, **outcome})

    return results
