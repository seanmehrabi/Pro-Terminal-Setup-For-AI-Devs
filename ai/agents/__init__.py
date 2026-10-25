"""Coding-agent registry and non-invasive presence probes."""

from __future__ import annotations

from ai.agents.scan import probe
from ai.agents.registry import list_agents
from ai.agents.report import render_report

__all__ = ["list_agents", "probe", "render_report"]
