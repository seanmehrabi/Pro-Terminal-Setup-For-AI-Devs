"""Best-effort GPU description for recommendations."""

from __future__ import annotations

import re
import subprocess
import sys


def gpu_note() -> str | None:
    """Return a short GPU label on macOS when detection is quick; else None."""
    if sys.platform != "darwin":
        return None
    return _mac_gpu_note()


def _mac_gpu_note() -> str | None:
    try:
        proc = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    names: list[str] = []
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        match = re.match(r"Chipset Model:\s*(.+)", stripped)
        if match:
            name = match.group(1).strip()
            if name and name not in names:
                names.append(name)
    if not names:
        return None
    if len(names) == 1:
        return names[0]
    return "; ".join(names)
