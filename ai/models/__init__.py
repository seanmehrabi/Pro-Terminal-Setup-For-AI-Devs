"""Optional local model recommendations and runtime probes."""

from __future__ import annotations

from ai.models.endpoints import endpoints_status
from ai.models.gpu import gpu_note
from ai.models.recommend import recommend

__all__ = ["recommend", "endpoints_status", "gpu_note"]
