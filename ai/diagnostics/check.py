"""Human-readable check output."""

from __future__ import annotations

from typing import Any, Dict, List


def format_check(host: Dict[str, Any], applications: List[Dict[str, Any]]) -> str:
    lines = [
        "AI workstation check",
        "  OS: {} ({})".format(host.get("os"), host.get("arch")),
        "  Homebrew: {}".format("yes" if host.get("brew") else "no"),
        "  Winget: {}".format("yes" if host.get("winget") else "no"),
        "",
        "Applications:",
    ]
    for row in applications:
        status = "installed" if row.get("installed") else "missing"
        version = row.get("version") or ""
        extra = " ({})".format(version) if version else ""
        action = row.get("action") or ""
        detail = row.get("detail") or ""
        tail = ""
        if action and action != "skip":
            tail = " — {}: {}".format(action, detail)
        lines.append("  - {}: {}{}{}".format(row.get("id"), status, extra, tail))
    return "\n".join(lines) + "\n"
