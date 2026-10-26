"""macOS install/detect adapter (Homebrew, npm, pip, VS Code extensions)."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

_PLATFORM_KEYS = (
    "method",
    "package",
    "detect_app",
    "detect_cmd",
    "version_cmd",
    "verified",
    "limitation",
    "fallback_method",
    "fallback_note",
    "official_url",
)

Runner = Callable[..., subprocess.CompletedProcess[Any]]


def _default_runner(
    args: List[str],
    *,
    shell: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        args,
        shell=shell,
        check=check,
        capture_output=True,
        text=True,
    )


_runner: Runner = _default_runner


def set_runner(runner: Optional[Runner]) -> None:
    """Replace subprocess runner (for unit tests)."""
    global _runner
    _runner = runner or _default_runner


def _brew_bin(host: Dict[str, Any]) -> str:
    if host.get("brew_path"):
        return str(host["brew_path"])
    found = shutil.which("brew")
    if found:
        return found
    if os.path.isfile("/opt/homebrew/bin/brew"):
        return "/opt/homebrew/bin/brew"
    return "brew"


def _platform_cfg(app: Dict[str, Any]) -> Dict[str, Any]:
    platforms = app.get("platforms") or {}
    block: Dict[str, Any] = {}
    if isinstance(platforms, dict) and isinstance(platforms.get("macos"), dict):
        block = dict(platforms["macos"])
    elif app.get("method"):
        block = {k: app.get(k) for k in _PLATFORM_KEYS if app.get(k) is not None}

    for key in _PLATFORM_KEYS:
        if key not in block and app.get(key) is not None:
            block[key] = app[key]
    return block


def _run_shell(cmd: str) -> Tuple[int, str, str]:
    try:
        proc = _runner(cmd, shell=True)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        code = int(proc.returncode or 0)
        return code, out, err
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""


def _run_argv(argv: List[str]) -> Tuple[int, str, str]:
    try:
        proc = _runner(argv, shell=False)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        code = int(proc.returncode or 0)
        return code, out, err
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""


def _app_search_paths(detect_app: str, host: Dict[str, Any]) -> List[str]:
    home = host.get("home") or os.path.expanduser("~")
    name = detect_app.strip()
    if not name:
        return []
    roots = ["/Applications", os.path.join(home, "Applications")]
    return [os.path.join(root, name) for root in roots]


def _find_app_bundle(detect_app: str, host: Dict[str, Any]) -> Optional[str]:
    for path in _app_search_paths(detect_app, host):
        if os.path.isdir(path):
            return path
    return None


def _brew_list(kind: str, package: str, host: Dict[str, Any]) -> bool:
    if not package:
        return False
    brew = _brew_bin(host)
    flag = "--cask" if kind == "cask" else "--formula"
    code, out, _ = _run_argv([brew, "list", flag, package])
    if code == 0:
        return True
    code, out, _ = _run_argv([brew, "list", package])
    return code == 0 and package in out.split()


def _vscode_extension_installed(ext_id: str) -> bool:
    code_bin = shutil.which("code")
    if not code_bin or not ext_id:
        return False
    code, out, _ = _run_argv([code_bin, "--list-extensions"])
    if code != 0:
        return False
    needle = ext_id.strip().lower()
    for line in out.splitlines():
        if line.strip().lower() == needle:
            return True
    return False


def _pip_user_site_binary(name: str) -> Optional[str]:
    home = os.path.expanduser("~")
    for sub in (
        os.path.join(home, "Library", "Python", "3.9", "bin", name),
        os.path.join(home, ".local", "bin", name),
    ):
        if os.path.isfile(sub) and os.access(sub, os.X_OK):
            return sub
    return shutil.which(name)


def _detect_installed(cfg: Dict[str, Any], host: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    method = str(cfg.get("method") or "")
    package = str(cfg.get("package") or "")
    detect_app = str(cfg.get("detect_app") or "").strip()
    detect_cmd = str(cfg.get("detect_cmd") or "").strip()

    if detect_app:
        path = _find_app_bundle(detect_app, host)
        if path:
            return True, path, method

    if detect_cmd:
        code, _, _ = _run_shell(detect_cmd)
        if code == 0:
            return True, None, method

    if method == "brew-cask" and _brew_list("cask", package, host):
        path = _find_app_bundle(detect_app, host) if detect_app else None
        return True, path, method

    if method == "brew-formula" and _brew_list("formula", package, host):
        return True, shutil.which(package), method

    if method == "npm" and package:
        bin_map = {
            "@openai/codex": "codex",
            "@anthropic-ai/claude-code": "claude",
            "@google/gemini-cli": "gemini",
        }
        bin_name = bin_map.get(package, package.split("/")[-1])
        path = shutil.which(bin_name)
        if path:
            return True, path, method

    if method == "pip" and package:
        base = package.split("[")[0].replace("_", "-")
        for name in (base, base.replace("-chat", ""), "aider"):
            path = _pip_user_site_binary(name)
            if path:
                return True, path, method

    if method == "vscode-extension" and _vscode_extension_installed(package):
        return True, shutil.which("code"), method

    if method in ("manual", "web-fallback", "pending", ""):
        return False, None, method

    return False, None, method


def _version_for(cfg: Dict[str, Any], host: Dict[str, Any], installed: bool, app_path: Optional[str]) -> Optional[str]:
    if not installed:
        return None

    version_cmd = str(cfg.get("version_cmd") or "").strip()
    if version_cmd:
        code, out, err = _run_shell(version_cmd)
        if code == 0 and out:
            return out.splitlines()[0].strip()
        if code == 0 and err:
            return err.splitlines()[0].strip()

    method = str(cfg.get("method") or "")
    package = str(cfg.get("package") or "")
    detect_cmd = str(cfg.get("detect_cmd") or "").strip()
    if detect_cmd:
        code, out, _ = _run_shell(detect_cmd)
        if code == 0 and out:
            line = out.splitlines()[0].strip()
            return line

    if method in ("brew-cask", "brew-formula") and package:
        brew = _brew_bin(host)
        argv = [brew, "info", "--json=v2"]
        if method == "brew-cask":
            argv.extend(["--cask", package])
        else:
            argv.append(package)
        code, out, _ = _run_argv(argv)
        if code == 0 and out:
            try:
                data = json.loads(out)
                if method == "brew-cask":
                    casks = data.get("casks") or []
                    if casks:
                        ver = casks[0].get("version")
                        if ver:
                            return str(ver)
                else:
                    formulae = data.get("formulae") or []
                    if formulae:
                        ver = formulae[0].get("versions", {}).get("stable")
                        if ver:
                            return str(ver)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    if app_path and app_path.endswith(".app"):
        plist = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.isfile(plist):
            code, out, _ = _run_argv(["defaults", "read", plist, "CFBundleShortVersionString"])
            if code == 0 and out:
                return out.strip()

    return None


def detect(app: Dict[str, Any], host: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _platform_cfg(app)
    method = str(cfg.get("method") or "")
    installed, path, detect_method = _detect_installed(cfg, host)
    version = _version_for(cfg, host, installed, path)
    return {
        "installed": installed,
        "version": version,
        "path": path,
        "method": detect_method or method,
    }


def _install_command(cfg: Dict[str, Any], host: Dict[str, Any]) -> Tuple[str, str]:
    method = str(cfg.get("method") or "")
    package = str(cfg.get("package") or "")
    brew = _brew_bin(host)

    if method == "brew-cask":
        return "install", "{} install --cask {}".format(brew, shlex.quote(package))
    if method == "brew-formula":
        return "install", "{} install {}".format(brew, shlex.quote(package))
    if method == "npm":
        return "install", "npm install -g {}".format(shlex.quote(package))
    if method == "pip":
        return "install", "pip3 install --user {}".format(shlex.quote(package))
    if method == "vscode-extension":
        code_bin = shutil.which("code") or "code"
        return "install", "{} --install-extension {}".format(shlex.quote(code_bin), shlex.quote(package))
    if method == "web-fallback":
        url = str(cfg.get("official_url") or app_official_url(cfg))
        return "web-fallback", "open {}".format(shlex.quote(url))
    return "manual", ""


def app_official_url(cfg: Dict[str, Any]) -> str:
    return str(cfg.get("official_url") or "")


def _mutate_command(cfg: Dict[str, Any], host: Dict[str, Any], operation: str) -> Tuple[str, str]:
    method = str(cfg.get("method") or "")
    package = str(cfg.get("package") or "")
    brew = _brew_bin(host)

    if method == "brew-cask":
        if operation == "update":
            return "update", "{} upgrade --cask {}".format(brew, shlex.quote(package))
        if operation == "uninstall":
            return "uninstall", "{} uninstall --cask {}".format(brew, shlex.quote(package))
        if operation == "repair":
            return "repair", "{} reinstall --cask {}".format(brew, shlex.quote(package))
        return _install_command(cfg, host)

    if method == "brew-formula":
        if operation == "update":
            return "update", "{} upgrade {}".format(brew, shlex.quote(package))
        if operation == "uninstall":
            return "uninstall", "{} uninstall {}".format(brew, shlex.quote(package))
        if operation == "repair":
            return "repair", "{} reinstall {}".format(brew, shlex.quote(package))
        return _install_command(cfg, host)

    if method == "npm":
        if operation == "update":
            return "update", "npm update -g {}".format(shlex.quote(package))
        if operation == "uninstall":
            return "uninstall", "npm uninstall -g {}".format(shlex.quote(package))
        if operation == "repair":
            return "repair", "npm install -g --force {}".format(shlex.quote(package))
        return _install_command(cfg, host)

    if method == "pip":
        if operation == "update":
            return "update", "pip3 install --user --upgrade {}".format(shlex.quote(package))
        if operation == "uninstall":
            return "uninstall", "pip3 uninstall -y {}".format(shlex.quote(package))
        if operation == "repair":
            return "repair", "pip3 install --user --force-reinstall {}".format(shlex.quote(package))
        return _install_command(cfg, host)

    if method == "vscode-extension":
        code_bin = shutil.which("code") or "code"
        if operation == "uninstall":
            return "uninstall", "{} --uninstall-extension {}".format(
                shlex.quote(code_bin), shlex.quote(package)
            )
        return _install_command(cfg, host)

    if operation == "install":
        return _install_command(cfg, host)
    return operation, ""


def _operation_result(
    app: Dict[str, Any],
    host: Dict[str, Any],
    dry_run: bool,
    operation: str,
) -> Dict[str, Any]:
    cfg = _platform_cfg(app)
    method = str(cfg.get("method") or "")
    verified = bool(cfg.get("verified"))

    if not method or method == "pending":
        return {
            "ok": False,
            "action": "unsupported",
            "detail": "installation method pending",
            "skipped": True,
        }

    if method == "manual" and not verified:
        limitation = str(cfg.get("limitation") or "manual installation required")
        return {"ok": False, "action": "manual", "detail": limitation, "skipped": True}

    if not verified and method != "web-fallback":
        limitation = str(cfg.get("limitation") or "not verified for automated install")
        return {"ok": False, "action": "manual", "detail": limitation, "skipped": True}

    if operation == "install":
        state = detect(app, host)
        if state.get("installed"):
            return {
                "ok": True,
                "action": "skip",
                "detail": "already installed",
                "skipped": True,
            }

    action_name, cmd = _mutate_command(cfg, host, operation)
    if not cmd:
        detail = str(cfg.get("limitation") or "no automated command for {}".format(operation))
        return {"ok": False, "action": "manual", "detail": detail, "skipped": True}

    if dry_run:
        return {"ok": True, "action": "dry-run", "detail": cmd, "skipped": False}

    code, out, err = _run_shell(cmd)
    if code == 0:
        detail = out or err or cmd
        return {"ok": True, "action": action_name, "detail": detail, "skipped": False}
    detail = err or out or "command failed (exit {})".format(code)
    return {"ok": False, "action": action_name, "detail": detail, "skipped": False}


def install(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _operation_result(app, host, dry_run, "install")


def update(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _operation_result(app, host, dry_run, "update")


def uninstall(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _operation_result(app, host, dry_run, "uninstall")


def repair(app: Dict[str, Any], host: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    return _operation_result(app, host, dry_run, "repair")
