"""Host memory helpers for model recommendations (stdlib only)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict


def memory_bytes_from_host(host: Dict[str, Any]) -> int:
    """Return RAM in bytes from host dict or OS detection."""
    raw = host.get("memory_bytes")
    if raw is not None:
        try:
            value = int(raw)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return _detect_system_memory_bytes()


def memory_gb_from_bytes(memory_bytes: int) -> float:
    if memory_bytes <= 0:
        return 0.0
    return round(memory_bytes / (1024**3), 1)


def _detect_system_memory_bytes() -> int:
    if sys.platform == "darwin":
        return _mac_memory_bytes()
    if sys.platform.startswith("linux"):
        return _linux_memory_bytes()
    if sys.platform == "win32":
        return _windows_memory_bytes()
    return 0


def _mac_memory_bytes() -> int:
    try:
        out = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return int(out.decode().strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _linux_memory_bytes() -> int:
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


def _windows_memory_bytes() -> int:
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
