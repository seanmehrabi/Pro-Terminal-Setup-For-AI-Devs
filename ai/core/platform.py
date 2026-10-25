"""Host platform detection for planning and adapters."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Any, Dict


def detect_host() -> Dict[str, Any]:
    """Detect OS, resources, and package managers available on this machine."""
    system = sys.platform
    os_name = "other"
    if system == "darwin":
        os_name = "macos"
    elif system == "win32":
        os_name = "windows"
    elif system.startswith("linux"):
        os_name = "linux"

    home = os.path.expanduser("~")
    memory_bytes = _memory_bytes(os_name)
    disk_free = _disk_free_bytes(home)

    return {
        "os": os_name,
        "arch": platform.machine(),
        "distro": _linux_distro() if os_name == "linux" else "",
        "memory_bytes": memory_bytes,
        "disk_free_bytes": disk_free,
        "home": home,
        "brew": shutil.which("brew") is not None,
        "winget": shutil.which("winget") is not None,
    }


def _memory_bytes(os_name: str) -> int:
    if os_name == "macos":
        return _mac_memory()
    if os_name == "linux":
        return _linux_memory()
    if os_name == "windows":
        return _windows_memory()
    return 0


def _mac_memory() -> int:
    try:
        import subprocess

        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL)
        return int(out.decode().strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _linux_memory() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1]) * 1024
    except OSError:
        pass
    return 0


def _windows_memory() -> int:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.ullTotalPhys)
    except (AttributeError, OSError, ValueError):
        pass
    return 0


def _disk_free_bytes(path: str) -> int:
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return 0


def _linux_distro() -> str:
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as fh:
            data: Dict[str, str] = {}
            for line in fh:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                data[key] = val.strip().strip('"')
            return data.get("ID", data.get("NAME", ""))
    except OSError:
        return ""
