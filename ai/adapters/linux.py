"""Linux install adapter (apt/dnf allowlist, manual, guarded remote scripts)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional

PKG_ALLOWLIST: Dict[str, Dict[str, str]] = {
    "git": {"apt": "git", "dnf": "git"},
    "python": {"apt": "python3", "dnf": "python3"},
    "node": {"apt": "nodejs", "dnf": "nodejs"},
    "gh": {"apt": "gh", "dnf": "gh"},
    "curl": {"apt": "curl", "dnf": "curl"},
}

DETECT_BINARIES: Dict[str, str] = {
    "git": "git",
    "python": "python3",
    "node": "node",
    "gh": "gh",
    "curl": "curl",
    "ollama": "ollama",
    "vscode": "code",
    "aider": "aider",
    "codex": "codex",
    "claude-code": "claude",
    "gemini-cli": "gemini",
    "opencode": "opencode",
}

APT_DISTROS = frozenset(
    {
        "debian",
        "ubuntu",
        "linuxmint",
        "pop",
        "elementary",
        "zorin",
        "kali",
        "raspbian",
    }
)
DNF_DISTROS = frozenset(
    {
        "fedora",
        "rhel",
        "centos",
        "rocky",
        "almalinux",
        "ol",
    }
)

SCRIPT_OPT_IN_ENV = "PRO_TERMINAL_ALLOW_SCRIPTS"


def detect(app: Dict[str, Any], host: Dict[str, Any]) -> Dict[str, Any]:
    """Return installation probe for app on this host."""
    if not _runtime_linux():
        return _detect_result(installed=False)

    app_id = str(app.get("id") or "")
    binary = DETECT_BINARIES.get(app_id)
    if not binary:
        return _detect_result(installed=False)

    path = shutil.which(binary)
    if not path:
        return _detect_result(installed=False)

    version = _read_version(binary)
    method = _detect_method(app, host, app_id)
    return _detect_result(installed=True, version=version, path=path, method=method)


def install(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _mutate(app, host, dry_run, action="install")


def update(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _mutate(app, host, dry_run, action="update")


def uninstall(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _mutate(app, host, dry_run, action="uninstall")


def repair(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _mutate(app, host, dry_run, action="repair")


def _mutate(
    app: Dict[str, Any],
    host: Dict[str, Any],
    dry_run: bool,
    action: str,
) -> Dict[str, Any]:
    if not _host_linux(host):
        return _op_result(
            ok=False,
            action=action,
            detail="host os is not linux",
            skipped=True,
        )

    app_id = str(app.get("id") or "")
    entry = _linux_entry(app)
    method = str(entry.get("method") or "manual").strip().lower()

    pkg_cmd = _package_manager_command(app_id, host, action)
    if pkg_cmd is not None:
        return _execute_or_plan(pkg_cmd, dry_run, action)

    if method == "script":
        url = str(entry.get("package") or "").strip()
        if not url:
            return _op_result(ok=False, action=action, detail="script install missing package URL")
        cmd = "curl -fsSL {} | sh".format(url)
        if dry_run:
            return _op_result(ok=True, action="dry-run", detail=cmd, skipped=False)
        if os.environ.get(SCRIPT_OPT_IN_ENV) != "1":
            return _op_result(
                ok=False,
                action=action,
                detail=(
                    "remote script install blocked; set {}=1 to opt in".format(SCRIPT_OPT_IN_ENV)
                ),
            )
        if not _runtime_linux():
            return _op_result(ok=False, action=action, detail="script install requires Linux runtime")
        return _run_shell(cmd, action)

    if method in ("manual", "web-fallback", "pending", ""):
        return _manual_result(app, entry, dry_run, action)

    if method in ("apt", "dnf"):
        return _op_result(
            ok=False,
            action=action,
            detail="catalog method {} is informational only; use manual or allowlist ids".format(method),
            skipped=not dry_run,
        )

    return _op_result(ok=False, action=action, detail="unsupported method: {}".format(method))


def _manual_result(
    app: Dict[str, Any],
    entry: Dict[str, Any],
    dry_run: bool,
    action: str,
) -> Dict[str, Any]:
    url = str(entry.get("official_url") or app.get("official_url") or "").strip()
    limitation = str(entry.get("limitation") or "manual installation required").strip()
    if method_is_web(entry):
        planned = "web-fallback: open {}".format(url or "(see official_url)")
    else:
        planned = "manual: {} {}".format(limitation, url).strip()
    if dry_run:
        return _op_result(ok=True, action="dry-run", detail=planned, skipped=False)
    detail = limitation
    if url:
        detail = "{} — {}".format(limitation, url)
    return _op_result(ok=False, action="manual", detail=detail, skipped=True)


def method_is_web(entry: Dict[str, Any]) -> bool:
    return str(entry.get("method") or "").strip().lower() == "web-fallback"


def _package_manager_command(app_id: str, host: Dict[str, Any], action: str) -> Optional[str]:
    if app_id not in PKG_ALLOWLIST:
        return None
    pm = _package_manager(_distro_id(host))
    if pm is None:
        return None
    pkg = PKG_ALLOWLIST[app_id].get(pm)
    if not pkg:
        return None
    if action == "install":
        return _install_cmd(pm, pkg)
    if action == "update":
        return _update_cmd(pm, pkg)
    if action == "uninstall":
        return _remove_cmd(pm, pkg)
    if action == "repair":
        return _repair_cmd(pm, pkg)
    return None


def _install_cmd(pm: str, pkg: str) -> str:
    if pm == "apt":
        return "sudo apt-get update && sudo apt-get install -y {}".format(pkg)
    return "sudo dnf install -y {}".format(pkg)


def _update_cmd(pm: str, pkg: str) -> str:
    if pm == "apt":
        return "sudo apt-get install -y --only-upgrade {}".format(pkg)
    return "sudo dnf upgrade -y {}".format(pkg)


def _remove_cmd(pm: str, pkg: str) -> str:
    if pm == "apt":
        return "sudo apt-get remove -y {}".format(pkg)
    return "sudo dnf remove -y {}".format(pkg)


def _repair_cmd(pm: str, pkg: str) -> str:
    if pm == "apt":
        return "sudo apt-get install -y --reinstall {}".format(pkg)
    return "sudo dnf reinstall -y {}".format(pkg)


def _execute_or_plan(cmd: str, dry_run: bool, action: str) -> Dict[str, Any]:
    if dry_run:
        return _op_result(ok=True, action="dry-run", detail=cmd, skipped=False)
    if not _runtime_linux():
        return _op_result(ok=False, action=action, detail="package manager action requires Linux runtime")
    return _run_shell(cmd, action)


def _run_shell(cmd: str, action: str) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _op_result(ok=False, action=action, detail=str(exc))
    if proc.returncode == 0:
        detail = (proc.stdout or "").strip() or "completed"
        return _op_result(ok=True, action=action, detail=detail)
    err = (proc.stderr or proc.stdout or "").strip() or "exit {}".format(proc.returncode)
    return _op_result(ok=False, action=action, detail=err)


def _read_version(binary: str) -> str:
    for args in ([binary, "--version"], [binary, "-V"], [binary, "-v"]):
        try:
            proc = subprocess.run(
                args,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        line = (proc.stdout or "").strip().splitlines()
        if not line:
            continue
        return _normalize_version(line[0])
    return ""


def _normalize_version(line: str) -> str:
    match = re.search(r"(\d+\.\d+(?:\.\d+)*)", line)
    if match:
        return match.group(1)
    return line[:80]


def _detect_method(app: Dict[str, Any], host: Dict[str, Any], app_id: str) -> str:
    if app_id in PKG_ALLOWLIST and _package_manager(_distro_id(host)):
        return "distro-package"
    entry = _linux_entry(app)
    return str(entry.get("method") or "")


def _linux_entry(app: Dict[str, Any]) -> Dict[str, Any]:
    platforms = app.get("platforms") or {}
    if not isinstance(platforms, dict):
        return {}
    entry = platforms.get("linux") or {}
    return entry if isinstance(entry, dict) else {}


def _distro_id(host: Dict[str, Any]) -> str:
    distro = str(host.get("distro") or "").strip().lower()
    if distro:
        return distro
    if not _runtime_linux():
        return ""
    return _read_os_release_id()


def _read_os_release_id() -> str:
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("ID="):
                    return line.split("=", 1)[1].strip().strip('"').lower()
    except OSError:
        pass
    return ""


def _package_manager(distro_id: str) -> Optional[str]:
    if not distro_id:
        return None
    if distro_id in APT_DISTROS or distro_id.endswith("ubuntu") or distro_id.endswith("debian"):
        return "apt"
    if distro_id in DNF_DISTROS:
        return "dnf"
    return None


def _runtime_linux() -> bool:
    return sys.platform.startswith("linux")


def _host_linux(host: Dict[str, Any]) -> bool:
    return host.get("os") == "linux"


def _detect_result(
    installed: bool,
    version: str = "",
    path: str = "",
    method: str = "",
) -> Dict[str, Any]:
    return {
        "installed": installed,
        "version": version,
        "path": path,
        "method": method,
    }


def _op_result(
    ok: bool,
    action: str,
    detail: str,
    skipped: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": ok,
        "action": action,
        "detail": detail,
        "skipped": skipped,
    }
