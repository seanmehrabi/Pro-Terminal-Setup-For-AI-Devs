"""Platform keychain / credential store backends (stdlib only)."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from typing import Callable, List, Optional, Tuple

SERVICE_NAME = "pro-terminal-setup"

RunnerResult = Tuple[int, str, str]
Runner = Callable[..., RunnerResult]

_LOG = logging.getLogger(__name__)

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\b(?:api[_-]?key|token|password|passwd|secret)[=:\s]+[^\s'\"]{8,}", re.I),
    re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"),
    re.compile(r"-w\s+\S+"),
    re.compile(r"/pass:\S+", re.I),
)


def account_key(provider: str, name: str) -> str:
    return f"{provider}:{name}"


def redact(text: str) -> str:
    """Mask substrings that look like secret material."""
    if not text:
        return text
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def macos_add_command(account: str, value: str) -> List[str]:
    return [
        "security",
        "add-generic-password",
        "-U",
        "-s",
        SERVICE_NAME,
        "-a",
        account,
        "-w",
        value,
    ]


def macos_find_command(account: str) -> List[str]:
    return [
        "security",
        "find-generic-password",
        "-s",
        SERVICE_NAME,
        "-a",
        account,
        "-w",
    ]


def macos_delete_command(account: str) -> List[str]:
    return [
        "security",
        "delete-generic-password",
        "-s",
        SERVICE_NAME,
        "-a",
        account,
    ]


def windows_set_command(account: str, value: str) -> List[str]:
    target = f"{SERVICE_NAME}:{account}"
    return [
        "cmdkey",
        f"/generic:{target}",
        f"/user:{account}",
        f"/pass:{value}",
    ]


def windows_delete_command(account: str) -> List[str]:
    target = f"{SERVICE_NAME}:{account}"
    return ["cmdkey", f"/delete:{target}"]


def linux_store_command(account: str) -> List[str]:
    return [
        "secret-tool",
        "store",
        "--label",
        f"{SERVICE_NAME} {account}",
        "service",
        SERVICE_NAME,
        "account",
        account,
    ]


def linux_lookup_command(account: str) -> List[str]:
    return [
        "secret-tool",
        "lookup",
        "service",
        SERVICE_NAME,
        "account",
        account,
    ]


def linux_clear_command(account: str) -> List[str]:
    return [
        "secret-tool",
        "clear",
        "service",
        SERVICE_NAME,
        "account",
        account,
    ]


def _default_runner(
    cmd: List[str],
    *,
    input: Optional[str] = None,
) -> RunnerResult:
    try:
        completed = subprocess.run(
            cmd,
            input=input,
            text=True,
            capture_output=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _LOG.warning("command failed: %s", redact(" ".join(cmd)))
        return 1, "", str(exc)
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def _os_kind() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return "unsupported"


def backend_name() -> str:
    kind = _os_kind()
    if kind == "macos":
        return "macos-keychain"
    if kind == "windows":
        return "windows-cmdkey-limited"
    if kind == "linux":
        return "linux-secret-tool"
    return "unsupported"


def set_secret(
    provider: str,
    name: str,
    value: str,
    runner: Runner = _default_runner,
) -> dict:
    account = account_key(provider, name)
    kind = _os_kind()

    if kind == "macos":
        rc, out, err = runner(macos_add_command(account, value))
        if rc == 0:
            return {"ok": True, "detail": "stored"}
        detail = (err or out or "keychain store failed").strip()
        _LOG.info("set_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "keychain store failed"}

    if kind == "windows":
        rc, out, err = runner(windows_set_command(account, value))
        if rc == 0:
            return {"ok": True, "detail": "stored"}
        detail = (err or out or "cmdkey store failed").strip()
        _LOG.info("set_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "cmdkey store failed"}

    if kind == "linux":
        if shutil.which("secret-tool") is None:
            return {
                "ok": False,
                "detail": (
                    "Install libsecret-tools (secret-tool). "
                    "Refusing to store secrets in plaintext."
                ),
            }
        rc, out, err = runner(linux_store_command(account), input=value)
        if rc == 0:
            return {"ok": True, "detail": "stored"}
        detail = (err or out or "secret-tool store failed").strip()
        _LOG.info("set_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "secret-tool store failed"}

    return {
        "ok": False,
        "detail": "No supported OS secret backend; refusing plaintext storage.",
    }


def get_secret(
    provider: str,
    name: str,
    runner: Runner = _default_runner,
) -> dict:
    account = account_key(provider, name)
    kind = _os_kind()

    if kind == "macos":
        rc, out, err = runner(macos_find_command(account))
        if rc == 0:
            return {"ok": True, "value": out.rstrip("\n")}
        detail = (err or out or "not found").strip()
        _LOG.info("get_secret miss for %s: %s", account, redact(detail))
        return {"ok": False, "detail": "not found"}

    if kind == "windows":
        return {
            "ok": False,
            "detail": (
                "Credential Manager retrieval requires the win32 API; "
                "cmdkey cannot read stored passwords."
            ),
        }

    if kind == "linux":
        if shutil.which("secret-tool") is None:
            return {
                "ok": False,
                "detail": (
                    "Install libsecret-tools (secret-tool). "
                    "Refusing to store secrets in plaintext."
                ),
            }
        rc, out, err = runner(linux_lookup_command(account))
        if rc == 0:
            return {"ok": True, "value": out.rstrip("\n")}
        _LOG.info("get_secret miss for %s: %s", account, redact((err or out).strip()))
        return {"ok": False, "detail": "not found"}

    return {
        "ok": False,
        "detail": "No supported OS secret backend; refusing plaintext storage.",
    }


def delete_secret(
    provider: str,
    name: str,
    runner: Runner = _default_runner,
) -> dict:
    account = account_key(provider, name)
    kind = _os_kind()

    if kind == "macos":
        rc, out, err = runner(macos_delete_command(account))
        if rc == 0:
            return {"ok": True, "detail": "deleted"}
        detail = (err or out or "keychain delete failed").strip()
        _LOG.info("delete_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "keychain delete failed"}

    if kind == "windows":
        rc, out, err = runner(windows_delete_command(account))
        if rc == 0:
            return {"ok": True, "detail": "deleted"}
        detail = (err or out or "cmdkey delete failed").strip()
        _LOG.info("delete_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "cmdkey delete failed"}

    if kind == "linux":
        if shutil.which("secret-tool") is None:
            return {
                "ok": False,
                "detail": (
                    "Install libsecret-tools (secret-tool). "
                    "Refusing to store secrets in plaintext."
                ),
            }
        rc, out, err = runner(linux_clear_command(account))
        if rc == 0:
            return {"ok": True, "detail": "deleted"}
        detail = (err or out or "secret-tool clear failed").strip()
        _LOG.info("delete_secret failed for %s: %s", account, redact(detail))
        return {"ok": False, "detail": redact(detail) or "secret-tool clear failed"}

    return {
        "ok": False,
        "detail": "No supported OS secret backend; refusing plaintext storage.",
    }
