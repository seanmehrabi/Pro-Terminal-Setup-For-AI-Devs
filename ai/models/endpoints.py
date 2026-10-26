"""Local inference runtime reachability (no downloads, no server startup)."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

LM_STUDIO_HOST = "127.0.0.1"
LM_STUDIO_PORT = 1234
LM_STUDIO_MODELS_URL = "http://127.0.0.1:1234/v1/models"

TCP_TIMEOUT_S = 0.3
HTTP_TIMEOUT_S = 1.0


def endpoints_status() -> Dict[str, Any]:
    """Probe Ollama and LM Studio on localhost (TCP, optional HTTP)."""
    return {
        "ollama": _probe_endpoint(
            OLLAMA_HOST,
            OLLAMA_PORT,
            OLLAMA_TAGS_URL,
        ),
        "lm_studio": _probe_endpoint(
            LM_STUDIO_HOST,
            LM_STUDIO_PORT,
            LM_STUDIO_MODELS_URL,
        ),
    }


def _probe_endpoint(host: str, port: int, http_url: str) -> Dict[str, Any]:
    tcp_open = tcp_reachable(host, port, TCP_TIMEOUT_S)
    http_ok: Optional[bool] = None
    if tcp_open:
        http_ok = http_reachable(http_url, HTTP_TIMEOUT_S)
    return {
        "host": host,
        "port": port,
        "tcp_open": tcp_open,
        "http_ok": http_ok,
    }


def tcp_reachable(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_reachable(url: str, timeout: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False
