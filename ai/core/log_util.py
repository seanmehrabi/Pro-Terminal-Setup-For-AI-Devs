"""Append-only logging for AI setup runs."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional


LOG_DIR = os.path.join(os.path.expanduser("~"), ".cache", "pro-terminal-setup")
LOG_FILE = os.path.join(LOG_DIR, "ai-setup.log")


def append_log(message: str, log_path: Optional[str] = None) -> None:
    path = log_path or LOG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = "[{}] {}\n".format(stamp, message)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
