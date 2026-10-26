"""Windows installation adapter (WinGet, PowerShell detection)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

RunCommandFn = Callable[[List[str], bool], Tuple[int, str, str]]

_run_command_impl: Optional[RunCommandFn] = None


def _default_run_command(argv: List[str], shell: bool) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            shell=shell,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)


def _run_command(argv: List[str], shell: bool = False) -> Tuple[int, str, str]:
    runner = _run_command_impl or _default_run_command
    return runner(argv, shell)


def _platform_entry(app: Dict[str, Any]) -> Dict[str, Any]:
    platforms = app.get("platforms") or {}
    if not isinstance(platforms, dict):
        return {}
    entry = platforms.get("windows")
    if isinstance(entry, dict):
        return entry
    return {}


def _is_windows(host: Dict[str, Any]) -> bool:
    return host.get("os") == "windows"


def _expand_windows_path(raw: str) -> str:
    if not raw:
        return ""
    out = os.path.expandvars(raw)
    out = os.path.expanduser(out)
    return out


def _winget_install_line(package: str) -> str:
    return (
        "winget install --id {} -e --accept-package-agreements --accept-source-agreements"
    ).format(package)


def _winget_upgrade_line(package: str) -> str:
    return "winget upgrade --id {} -e --accept-package-agreements --accept-source-agreements".format(
        package
    )


def _winget_uninstall_line(package: str) -> str:
    return "winget uninstall --id {} -e --accept-source-agreements".format(package)


def _winget_repair_line(package: str) -> str:
    return (
        "winget install --id {} -e --force --accept-package-agreements --accept-source-agreements"
    ).format(package)


def _winget_list_line(package: str) -> str:
    return "winget list --id {} --accept-source-agreements".format(package)


def _parse_winget_list_version(output: str, package: str) -> str:
    for line in output.splitlines():
        if package.lower() in line.lower():
            parts = re.split(r"\s{2,}|\t", line.strip())
            if len(parts) >= 2:
                candidate = parts[-1].strip()
                if candidate and not candidate.lower().startswith("version"):
                    return candidate
    return ""


def _detect_via_winget(package: str) -> Tuple[bool, str, str]:
    if not package:
        return False, "", ""
    code, out, err = _run_command(
        [
            "winget",
            "list",
            "--id",
            package,
            "--accept-source-agreements",
        ]
    )
    combined = (out or "") + (err or "")
    if code != 0:
        return False, "", ""
    version = _parse_winget_list_version(combined, package)
    return True, version, "winget"


def _detect_via_command(name: str) -> Tuple[bool, str, str]:
    if not name:
        return False, "", ""
    if shutil.which(name):
        return True, "", "path"
    code, out, _ = _run_command(["where.exe", name])
    if code == 0 and out.strip():
        first = out.strip().splitlines()[0].strip()
        return True, "", first
    ps = (
        "Get-Command {name} -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty Source"
    ).format(name=name)
    code, out, _ = _run_command(["powershell", "-NoProfile", "-Command", ps])
    if code == 0 and out.strip():
        return True, "", out.strip().splitlines()[0].strip()
    return False, "", ""


def _detect_via_app_path(path_template: str) -> Tuple[bool, str, str]:
    path = _expand_windows_path(path_template)
    if path and os.path.isfile(path):
        return True, "", path
    return False, "", ""


def _detect_version(version_cmd: str) -> str:
    if not version_cmd:
        return ""
    parts = version_cmd.split()
    if not parts:
        return ""
    code, out, err = _run_command(parts)
    if code != 0:
        return ""
    text = (out or err or "").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def detect(app: Dict[str, Any], host: Dict[str, Any]) -> Dict[str, Any]:
    """Return installed state for an application on Windows (no-op elsewhere)."""
    if not _is_windows(host):
        return {
            "installed": False,
            "version": "",
            "path": "",
            "method": "skipped-not-windows",
        }

    entry = _platform_entry(app)
    method = str(entry.get("method") or "").strip()
    package = str(entry.get("package") or "").strip()
    detect_cmd = str(entry.get("detect_cmd") or "").strip()
    detect_app = str(entry.get("detect_app") or "").strip()
    version_cmd = str(entry.get("version_cmd") or "").strip()

    installed = False
    version = ""
    path = ""
    detect_method = ""

    if method == "winget" and package:
        installed, version, detect_method = _detect_via_winget(package)

    if not installed and detect_app:
        installed, _, path = _detect_via_app_path(detect_app)
        if installed:
            detect_method = "path"

    if not installed and detect_cmd:
        installed, _, path = _detect_via_command(detect_cmd)
        if installed:
            detect_method = "command"

    if installed and not version and version_cmd:
        version = _detect_version(version_cmd)

    if not detect_method and installed:
        detect_method = method or "unknown"

    return {
        "installed": installed,
        "version": version,
        "path": path,
        "method": detect_method,
    }


def _manual_detail(entry: Dict[str, Any]) -> str:
    url = str(entry.get("official_url") or "").strip()
    note = str(entry.get("fallback_note") or "").strip()
    if note and url:
        return "{} ({})".format(note, url)
    if url:
        return "manual install: {}".format(url)
    if note:
        return note
    return "manual installation required"


def _winget_op(
    app: Dict[str, Any],
    host: Dict[str, Any],
    dry_run: bool,
    action: str,
    line_builder: Callable[[str], str],
) -> Dict[str, Any]:
    entry = _platform_entry(app)
    method = str(entry.get("method") or "").strip()
    package = str(entry.get("package") or "").strip()

    if method == "manual" or not package:
        detail = _manual_detail(entry)
        if dry_run:
            return {"ok": True, "action": "dry-run", "detail": detail, "skipped": False}
        return {"ok": False, "action": action, "detail": detail, "skipped": True}

    cmd_line = line_builder(package)

    if not _is_windows(host):
        if dry_run:
            return {"ok": True, "action": "dry-run", "detail": cmd_line, "skipped": False}
        return {
            "ok": False,
            "action": action,
            "detail": "Windows host required",
            "skipped": True,
        }

    if dry_run:
        return {"ok": True, "action": "dry-run", "detail": cmd_line, "skipped": False}

    argv = cmd_line.split()
    code, out, err = _run_command(argv)
    detail = (out or err or cmd_line).strip()
    if code != 0:
        return {"ok": False, "action": action, "detail": detail, "skipped": False}
    return {"ok": True, "action": action, "detail": detail or cmd_line, "skipped": False}


def install(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _winget_op(app, host, dry_run, "install", _winget_install_line)


def update(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _winget_op(app, host, dry_run, "update", _winget_upgrade_line)


def uninstall(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _winget_op(app, host, dry_run, "uninstall", _winget_uninstall_line)


def repair(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _winget_op(app, host, dry_run, "repair", _winget_repair_line)
