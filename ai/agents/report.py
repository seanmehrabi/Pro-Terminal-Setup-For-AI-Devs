"""Plain-text reports for coding-agent probes."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence


def render_report(probes: Sequence[Dict[str, Any]]) -> str:
    lines = ["Coding agents", ""]
    for row in probes:
        agent_id = row.get("id") or "?"
        name = row.get("name") or agent_id
        kind = row.get("kind") or "unknown"
        status = "installed" if row.get("installed") else "missing"
        verified = "verified" if row.get("verified") else "unverified"
        parts = ["  - {} ({}) [{}]: {}".format(name, agent_id, kind, status)]
        parts.append("    registry: {}".format(verified))
        version = row.get("version") or ""
        if version:
            parts.append("    version: {}".format(version))
        command = row.get("command") or ""
        if command:
            parts.append("    command: {}".format(command))
        extension_id = row.get("extension_id") or ""
        if extension_id:
            parts.append("    extension: {}".format(extension_id))
        if row.get("vscode_checked") is False and kind == "vscode-extension":
            parts.append("    vscode: code CLI not available (extensions not checked)")
        optional_ver = row.get("optional_cli_version") or ""
        if row.get("optional_cli_installed"):
            parts.append("    optional cli: gh copilot ({})".format(optional_ver or "present"))
        note = row.get("note") or ""
        if note:
            parts.append("    note: {}".format(note))
        lines.extend(parts)
    return "\n".join(lines) + "\n"
