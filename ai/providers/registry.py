"""Static metadata for supported AI providers (no secrets)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "kind": "cloud",
        "auth": "api-key",
        "secret_names": ["api_key"],
        "default_base_url": "https://api.openai.com/v1",
        "official_url": "https://platform.openai.com",
        "auth_note": (
            "A ChatGPT Plus, Team, or Enterprise subscription does not include OpenAI "
            "API access. Create a separate API key at platform.openai.com for programmatic use."
        ),
    },
    "anthropic": {
        "id": "anthropic",
        "name": "Anthropic",
        "kind": "cloud",
        "auth": "api-key",
        "secret_names": ["api_key"],
        "default_base_url": "https://api.anthropic.com",
        "official_url": "https://console.anthropic.com",
        "auth_note": (
            "A Claude Pro or Team chat subscription at claude.ai does not include Anthropic "
            "API access. Use the Anthropic Console to create an API key for the Claude API."
        ),
    },
    "google": {
        "id": "google",
        "name": "Google AI (Gemini)",
        "kind": "cloud",
        "auth": "api-key",
        "secret_names": ["api_key"],
        "default_base_url": "https://generativelanguage.googleapis.com",
        "official_url": "https://aistudio.google.com/apikey",
        "auth_note": (
            "Gemini in the Google app or gemini.google.com is separate from the Google AI "
            "Studio / Gemini API. Generate an API key in AI Studio for API access."
        ),
    },
    "github-copilot": {
        "id": "github-copilot",
        "name": "GitHub Copilot",
        "kind": "cloud",
        "auth": "token",
        "secret_names": ["github_token"],
        "default_base_url": "https://api.github.com",
        "official_url": "https://github.com/features/copilot",
        "auth_note": (
            "Copilot in your editor uses your GitHub account subscription. API or CLI "
            "integrations may require a personal access token with appropriate Copilot scopes."
        ),
    },
    "ollama": {
        "id": "ollama",
        "name": "Ollama",
        "kind": "local",
        "auth": "none",
        "secret_names": [],
        "default_base_url": "http://127.0.0.1:11434",
        "official_url": "https://ollama.com",
        "auth_note": "Runs locally; no cloud API key required.",
    },
    "lm-studio": {
        "id": "lm-studio",
        "name": "LM Studio",
        "kind": "local",
        "auth": "none",
        "secret_names": [],
        "default_base_url": "http://127.0.0.1:1234/v1",
        "official_url": "https://lmstudio.ai",
        "auth_note": "Runs locally via LM Studio's OpenAI-compatible server; no cloud API key required.",
    },
}


def list_providers() -> List[Dict[str, Any]]:
    """Return metadata for all registered providers (sorted by id)."""
    return [deepcopy(PROVIDERS[key]) for key in sorted(PROVIDERS.keys())]


def get_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    """Return a copy of provider metadata, or None if unknown."""
    entry = PROVIDERS.get(provider_id)
    if entry is None:
        return None
    return deepcopy(entry)
