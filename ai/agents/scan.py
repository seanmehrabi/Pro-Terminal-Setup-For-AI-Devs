"""Detect installed coding agents without modifying the system."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Sequence

from ai.agents.registry import agent_specs

ProbeRow = Dict[str, Any]

_VERSION_TIMEOUT = 3.0


def _first_on_path(candidates: Sequence[str], which_fn: Callable[[str], Optional[str]]) -> Optional[str]:
    for name in candidates:
        path = which_fn(name)
        if path:
            return path
    return None


def _run_version(argv: Sequence[str], timeout: float = _VERSION_TIMEOUT) -> str:
    if not argv:
        return ""
    cmd = list(argv)
    try:
        proc = subprocess.run(
            cmd + ["--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    out = (proc.stdout or proc.stderr or "").strip()
    if not out:
        return ""
    return out.splitlines()[0].strip()


def _list_vscode_extensions(code_path: str, timeout: float = _VERSION_TIMEOUT) -> Optional[List[str]]:
    try:
        proc = subprocess.run(
            [code_path, "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = []
    for line in (proc.stdout or "").splitlines():
        ext = line.strip()
        if ext:
            lines.append(ext)
    return lines


def _probe_cli(meta: Dict[str, Any], which_fn: Callable[[str], Optional[str]]) -> ProbeRow:
    candidates = meta.get("command_candidates") or []
    resolved = _first_on_path(candidates, which_fn)
    installed = bool(resolved)
    version = ""
    if resolved:
        version = _run_version([resolved])
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "kind": meta.get("kind"),
        "verified": bool(meta.get("verified")),
        "note": meta.get("note") or "",
        "installed": installed,
        "command": resolved or "",
        "version": version,
        "extension_id": "",
        "vscode_checked": False,
        "optional_cli_installed": False,
        "optional_cli_version": "",
    }


def _probe_vscode_extension(
    meta: Dict[str, Any],
    which_fn: Callable[[str], Optional[str]],
    extensions: Optional[List[str]],
    vscode_checked: bool,
) -> ProbeRow:
    ext_candidates = meta.get("extension_candidates") or []
    matched = ""
    if extensions is not None:
        for ext_id in ext_candidates:
            if ext_id in extensions:
                matched = ext_id
                break
    row: ProbeRow = {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "kind": meta.get("kind"),
        "verified": bool(meta.get("verified")),
        "note": meta.get("note") or "",
        "installed": bool(matched),
        "command": "",
        "version": "",
        "extension_id": matched,
        "vscode_checked": vscode_checked,
        "optional_cli_installed": False,
        "optional_cli_version": "",
    }
    optional = meta.get("optional_cli") or {}
    argv = optional.get("argv") or []
    if argv:
        cmd_name = str(argv[0])
        cmd_path = which_fn(cmd_name)
        if cmd_path:
            full_argv = [cmd_path] + [str(a) for a in argv[1:]]
            version = _run_version(full_argv)
            if version:
                row["optional_cli_installed"] = True
                row["optional_cli_version"] = version
    if row["installed"] or row["optional_cli_installed"]:
        row["installed"] = True
    return row


def _probe_desktop(meta: Dict[str, Any], which_fn: Callable[[str], Optional[str]]) -> ProbeRow:
    candidates = meta.get("command_candidates") or []
    resolved = _first_on_path(candidates, which_fn)
    paths = meta.get("desktop_paths") or []
    on_disk = any(os.path.exists(str(p)) for p in paths)
    installed = bool(resolved or on_disk)
    version = ""
    if resolved:
        version = _run_version([resolved])
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "kind": meta.get("kind"),
        "verified": bool(meta.get("verified")),
        "note": meta.get("note") or "",
        "installed": installed,
        "command": resolved or "",
        "version": version,
        "extension_id": "",
        "vscode_checked": False,
        "optional_cli_installed": False,
        "optional_cli_version": "",
    }


def probe(
    which_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> List[ProbeRow]:
    """Probe each registered agent; never installs or changes VS Code settings."""
    which = which_fn or shutil.which
    code_path = which("code")
    extensions: Optional[List[str]] = None
    vscode_checked = False
    if code_path:
        extensions = _list_vscode_extensions(code_path)
        vscode_checked = extensions is not None

    rows: List[ProbeRow] = []
    for meta in agent_specs():
        kind = meta.get("kind")
        if kind == "cli":
            rows.append(_probe_cli(meta, which))
        elif kind == "vscode-extension":
            rows.append(_probe_vscode_extension(meta, which, extensions, vscode_checked))
        elif kind == "desktop":
            rows.append(_probe_desktop(meta, which))
        else:
            rows.append(
                {
                    "id": meta.get("id"),
                    "name": meta.get("name"),
                    "kind": kind,
                    "verified": bool(meta.get("verified")),
                    "note": meta.get("note") or "",
                    "installed": False,
                    "command": "",
                    "version": "",
                    "extension_id": "",
                    "vscode_checked": vscode_checked,
                    "optional_cli_installed": False,
                    "optional_cli_version": "",
                }
            )
    return rows
