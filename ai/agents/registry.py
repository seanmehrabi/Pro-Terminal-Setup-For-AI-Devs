"""Canonical coding-agent metadata (report-only; no installs)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

AgentMeta = Dict[str, Any]

_AGENTS: List[AgentMeta] = [
    {
        "id": "codex",
        "name": "Codex CLI",
        "kind": "cli",
        "verified": True,
        "note": "",
        "command_candidates": ["codex"],
    },
    {
        "id": "claude-code",
        "name": "Claude Code",
        "kind": "cli",
        "verified": True,
        "note": "",
        "command_candidates": ["claude"],
    },
    {
        "id": "gemini-cli",
        "name": "Gemini CLI",
        "kind": "cli",
        "verified": True,
        "note": "",
        "command_candidates": ["gemini"],
    },
    {
        "id": "opencode",
        "name": "OpenCode",
        "kind": "cli",
        "verified": True,
        "note": "",
        "command_candidates": ["opencode"],
    },
    {
        "id": "cline",
        "name": "Cline",
        "kind": "vscode-extension",
        "verified": False,
        "note": "Extension id saoudrizwan.claude-dev is unverified in this registry.",
        "extension_candidates": ["saoudrizwan.claude-dev"],
    },
    {
        "id": "copilot",
        "name": "GitHub Copilot",
        "kind": "vscode-extension",
        "verified": True,
        "note": "",
        "extension_candidates": ["GitHub.copilot"],
        "optional_cli": {"argv": ["gh", "copilot"], "version_flag": "--version"},
    },
    {
        "id": "cursor",
        "name": "Cursor",
        "kind": "desktop",
        "verified": True,
        "note": "",
        "command_candidates": ["cursor"],
        "desktop_paths": [
            "/Applications/Cursor.app",
        ],
    },
]


_PUBLIC_KEYS = ("id", "name", "kind", "verified", "note")


def list_agents() -> List[AgentMeta]:
    """Return agent metadata rows for reporting (no probe state)."""
    rows: List[AgentMeta] = []
    for entry in _AGENTS:
        rows.append({key: entry.get(key) for key in _PUBLIC_KEYS})
    return rows


def agent_specs() -> List[AgentMeta]:
    """Full registry rows for probing (includes command/extension candidates)."""
    return deepcopy(_AGENTS)
