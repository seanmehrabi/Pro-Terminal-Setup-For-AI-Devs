"""Conservative local model suggestions from host RAM (no auto-download)."""

from __future__ import annotations

import platform
from typing import Any, Dict, List

from ai.models.gpu import gpu_note
from ai.models.memory import memory_bytes_from_host, memory_gb_from_bytes

Suggestion = Dict[str, Any]


def recommend(host: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest quantized models sized for available RAM; labels only for runtimes."""
    memory_bytes = memory_bytes_from_host(host)
    memory_gb = memory_gb_from_bytes(memory_bytes)
    arch = str(host.get("arch") or platform.machine())
    gpu = gpu_note()
    tier_note = _tier_banner(memory_gb)
    suggestions = _suggestions_for_memory_gb(memory_gb, tier_note)
    return {
        "memory_gb": memory_gb,
        "arch": arch,
        "gpu": gpu,
        "suggestions": suggestions,
    }


def _tier_banner(memory_gb: float) -> str:
    if memory_gb < 8:
        return (
            "Under 8 GB RAM: stick to tiny models; expect limited quality. "
            "Pull manually when ready (nothing is downloaded here)."
        )
    if memory_gb < 16:
        return (
            "8–16 GB RAM: 7B/8B-class quantized models are a practical fit. "
            "Pull manually when ready."
        )
    if memory_gb < 32:
        return (
            "16–32 GB RAM: 14B-class quantized models are reasonable. "
            "Pull manually when ready."
        )
    return (
        "32 GB+ RAM: larger models are optional; start conservative if unsure. "
        "Pull manually when ready."
    )


def _suggestions_for_memory_gb(memory_gb: float, tier_note: str) -> List[Suggestion]:
    if memory_gb < 8:
        base = [
            _entry(
                "phi3:mini",
                2.3,
                "Tiny instruct model; best effort on low RAM. " + tier_note,
            ),
            _entry(
                "llama3.2:1b-instruct-q4_K_M",
                1.0,
                "Very small; useful for smoke tests only. " + tier_note,
            ),
            _entry(
                "qwen2.5:0.5b-instruct-q4_K_M",
                0.5,
                "Minimal footprint; quality will be limited. " + tier_note,
            ),
        ]
        return _with_runtimes(base)

    if memory_gb < 16:
        base = [
            _entry(
                "llama3.1:8b-instruct-q4_K_M",
                4.9,
                "Solid default 8B quant for this RAM tier. " + tier_note,
            ),
            _entry(
                "mistral:7b-instruct-q4_K_M",
                4.1,
                "Efficient 7B instruct quant. " + tier_note,
            ),
            _entry(
                "gemma2:9b-instruct-q4_K_M",
                5.5,
                "Slightly larger; leave headroom for OS and apps. " + tier_note,
            ),
        ]
        return _with_runtimes(base)

    if memory_gb < 32:
        base = [
            _entry(
                "qwen2.5:14b-instruct-q4_K_M",
                9.0,
                "14B-class quant suited to this RAM band. " + tier_note,
            ),
            _entry(
                "llama3.1:8b-instruct-q4_K_M",
                4.9,
                "Lighter fallback if 14B feels tight alongside other apps. " + tier_note,
            ),
        ]
        return _with_runtimes(base)

    base = [
        _entry(
            "qwen2.5:14b-instruct-q4_K_M",
            9.0,
            "Conservative default before trying heavier weights. " + tier_note,
        ),
        _entry(
            "qwen2.5:32b-instruct-q4_K_M",
            19.0,
            "Optional larger quant; verify free RAM before loading. " + tier_note,
        ),
        _entry(
            "llama3.1:70b-instruct-q4_K_M",
            40.0,
            "Optional very large quant; may need most of system RAM. " + tier_note,
        ),
    ]
    return _with_runtimes(base)


def _entry(model_id: str, size_gb: float, note: str) -> Dict[str, Any]:
    return {"id": model_id, "size_gb": size_gb, "note": note}


def _with_runtimes(entries: List[Dict[str, Any]]) -> List[Suggestion]:
    out: List[Suggestion] = []
    for item in entries:
        for runtime in ("ollama", "lm-studio"):
            out.append(
                {
                    "id": item["id"],
                    "size_gb": item["size_gb"],
                    "note": item["note"],
                    "runtime": runtime,
                }
            )
    return out
