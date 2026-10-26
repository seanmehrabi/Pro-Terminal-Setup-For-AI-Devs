"""CLI entrypoint: python3 -m ai <command> [options] [app ids...]."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ai.adapters.base import get_adapter
from ai.core.catalog import load_catalog
from ai.core.engine import build_plan, run_plan, select_ids
from ai.core.log_util import append_log
from ai.core.platform import detect_host
from ai.diagnostics.check import format_check


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _catalog() -> Dict[str, Any]:
    return load_catalog(repo_root())


def _status_rows(catalog: Dict[str, Any], host: Dict[str, Any]) -> List[Dict[str, Any]]:
    adapter = get_adapter(host)
    rows: List[Dict[str, Any]] = []
    for app in catalog.get("applications") or []:
        app_id = app.get("id")
        if not app_id:
            continue
        detect_info = adapter.detect(app, host)
        plan = build_plan(catalog, host, [str(app_id)])
        action = plan[0].get("action") if plan else "unsupported"
        detail = plan[0].get("detail") if plan else ""
        rows.append(
            {
                "id": str(app_id),
                "installed": bool(detect_info.get("installed")),
                "version": detect_info.get("version") or "",
                "action": action,
                "detail": detail,
            }
        )
    return rows


def cmd_help() -> int:
    print(
        """Usage: python3 -m ai <command> [options] [app-id ...]

Commands:
  help              Show this message
  list              List catalog applications and profiles
  check             Human-readable status (exit 0)
  status            JSON status for host and applications
  dry-run           Plan installs without changing the system
  install           Install selected applications
  update            Update selected applications
  repair            Repair selected applications
  uninstall         Uninstall selected applications
  recommend-models  Optional local model hints (requires ai.models)

Options:
  --profile NAME    Include a profile (repeatable)
  --all             Include every catalog application
  --yes             Non-interactive confirmation for install

Examples:
  python3 -m ai list
  python3 -m ai dry-run --profile coding
  python3 -m ai install --yes cursor gh
"""
    )
    return 0


def cmd_list(catalog: Dict[str, Any]) -> int:
    print("Applications:")
    for app in catalog.get("applications") or []:
        profiles = app.get("profiles") or []
        prof = ", ".join(profiles) if isinstance(profiles, list) else ""
        print("  {} — {} ({}) [{}]".format(app.get("id"), app.get("name"), app.get("cost"), prof))
    print("\nProfiles:")
    for name, ids in sorted((catalog.get("profiles") or {}).items()):
        print("  {}: {}".format(name, ", ".join(ids)))
    return 0


def _parse_args(argv: Sequence[str]) -> Tuple[str, Dict[str, Any], List[str]]:
    if not argv:
        return "help", {}, []
    command = argv[0]
    if command not in {
        "help",
        "list",
        "check",
        "status",
        "dry-run",
        "install",
        "update",
        "repair",
        "uninstall",
        "recommend-models",
    }:
        command = "help"
        rest = list(argv)
    else:
        rest = list(argv[1:])

    opts: Dict[str, Any] = {"profiles": [], "all": False, "yes": False}
    positionals: List[str] = []
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--profile" and i + 1 < len(rest):
            opts["profiles"].append(rest[i + 1])
            i += 2
            continue
        if arg == "--all":
            opts["all"] = True
            i += 1
            continue
        if arg == "--yes":
            opts["yes"] = True
            i += 1
            continue
        if arg.startswith("--"):
            i += 1
            continue
        positionals.append(arg)
        i += 1
    return command, opts, positionals


def _resolve_ids(
    catalog: Dict[str, Any],
    opts: Dict[str, Any],
    positionals: List[str],
    command: str,
) -> Optional[List[str]]:
    ids = select_ids(
        catalog,
        opts.get("profiles") or None,
        bool(opts.get("all")),
        positionals or None,
    )
    if ids:
        return ids
    if command != "install":
        return ids
    if sys.stdin.isatty():
        print("No apps selected. Choose a profile name, 'all', or comma-separated app ids:")
        for name in sorted((catalog.get("profiles") or {}).keys()):
            print("  profile: {}".format(name))
        print("  all")
        try:
            line = input("> ").strip()
        except EOFError:
            line = ""
        if not line:
            return []
        if line.lower() == "all":
            return select_ids(catalog, None, True, None)
        if line in (catalog.get("profiles") or {}):
            return select_ids(catalog, [line], False, None)
        parts = [p.strip() for p in line.split(",") if p.strip()]
        return select_ids(catalog, None, False, parts)
    return []


def _providers_note() -> None:
    try:
        import ai.providers  # noqa: F401
    except ImportError:
        print("(Provider module not installed; config path: ~/.config/pro-terminal-setup/ai-config.json)")


def cmd_recommend_models(host: Dict[str, Any]) -> int:
    try:
        from ai.models.recommend import recommend
    except ImportError:
        print("Optional ai.models package is not installed; skipping model recommendations.")
        return 0
    rec = recommend(host)
    if isinstance(rec, str):
        print(rec)
    else:
        print(json.dumps(rec, indent=2))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    command, opts, positionals = _parse_args(args)
    append_log("command={} args={}".format(command, args))

    if command == "help":
        return cmd_help()

    catalog = _catalog()
    host = detect_host()

    if command == "list":
        return cmd_list(catalog)

    if command == "recommend-models":
        return cmd_recommend_models(host)

    if command in ("check", "status"):
        rows = _status_rows(catalog, host)
        if command == "status":
            payload = {"host": host, "applications": rows}
            print(json.dumps(payload, indent=2))
            return 0
        print(format_check(host, rows))
        _providers_note()
        return 0

    operation = "install"
    dry_run = False
    if command == "dry-run":
        dry_run = True
    elif command in ("update", "repair", "uninstall"):
        operation = command

    ids = _resolve_ids(catalog, opts, positionals, command if command == "install" else operation)
    if command == "install" and not ids:
        if not opts.get("yes") and not opts.get("all") and not positionals and not opts.get("profiles"):
            if not sys.stdin.isatty():
                print("Non-interactive install requires --yes and --profile, --all, or app ids.", file=sys.stderr)
                return 2
        if not ids:
            print("No applications selected.", file=sys.stderr)
            return 2

    if not ids and command != "install":
        print("No applications selected.", file=sys.stderr)
        return 2

    plan = build_plan(catalog, host, ids)
    for step in plan:
        append_log("plan {} {} -> {}".format(step.get("id"), step.get("action"), step.get("detail")))

    if dry_run or command == "dry-run":
        print("Dry run plan:")
        for step in plan:
            print("  {} ({}) — {}: {}".format(step.get("id"), step.get("name"), step.get("action"), step.get("detail")))
        results = run_plan(plan, host, catalog, dry_run=True, operation="install")
        append_log("dry-run complete steps={}".format(len(results)))
        return 0

    if command == "install" and not opts.get("yes") and not sys.stdin.isatty():
        print("Non-interactive install requires --yes.", file=sys.stderr)
        return 2

    results = run_plan(plan, host, catalog, dry_run=False, operation=operation)
    for row in results:
        print("{}: {} — {}".format(row.get("id"), row.get("action"), row.get("detail")))
        append_log("result {} {} ok={}".format(row.get("id"), row.get("action"), row.get("ok")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
