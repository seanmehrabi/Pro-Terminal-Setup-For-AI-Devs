"""Localhost TCP reachability checks for local inference servers."""

from __future__ import annotations

import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _parse_host_port(base_url: str) -> Optional[Tuple[str, int]]:
    if not base_url:
        return None
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host or host not in LOCAL_HOSTS:
        return None
    port = parsed.port
    if port is None:
        if parsed.scheme == "https":
            port = 443
        else:
            port = 80
    return host, port


def tcp_reachable(base_url: str, timeout: float = 0.3) -> bool:
    """Return True if a TCP connection to the localhost endpoint succeeds."""
    target = _parse_host_port(base_url)
    if target is None:
        return False
    host, port = target
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
