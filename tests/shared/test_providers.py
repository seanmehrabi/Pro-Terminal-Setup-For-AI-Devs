"""Provider registry, config, credentials, and status (no real home config or keychain)."""

from __future__ import annotations

import json
import sys
import unittest
from unittest import mock

from ai.providers import (
    DEFAULT_CONFIG_PATH,
    delete_secret,
    get_provider,
    get_secret,
    list_providers,
    load_preferences,
    set_preferences,
    set_secret,
    status,
)
from ai.providers.reachability import tcp_reachable


class TestProviderRegistry(unittest.TestCase):
    def test_list_providers_includes_all_ids(self) -> None:
        ids = {p["id"] for p in list_providers()}
        expected = {
            "openai",
            "anthropic",
            "google",
            "github-copilot",
            "ollama",
            "lm-studio",
        }
        self.assertEqual(ids, expected)

    def test_get_provider_unknown(self) -> None:
        self.assertIsNone(get_provider("not-a-provider"))

    def test_auth_notes_distinguish_chat_from_api(self) -> None:
        openai = get_provider("openai")
        anthropic = get_provider("anthropic")
        assert openai is not None
        assert anthropic is not None
        note_o = (openai.get("auth_note") or "").lower()
        note_a = (anthropic.get("auth_note") or "").lower()
        self.assertIn("chatgpt", note_o)
        self.assertIn("api", note_o)
        self.assertIn("claude", note_a)
        self.assertIn("api", note_a)

    def test_local_default_base_urls(self) -> None:
        ollama = get_provider("ollama")
        lm = get_provider("lm-studio")
        assert ollama is not None
        assert lm is not None
        self.assertEqual(ollama.get("default_base_url"), "http://127.0.0.1:11434")
        self.assertEqual(lm.get("default_base_url"), "http://127.0.0.1:1234/v1")


class TestPreferences(unittest.TestCase):
    def test_load_missing_file_is_empty(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + "/missing.json"
            data = load_preferences(path)
            self.assertEqual(data, {"providers": {}})

    def test_set_preferences_writes_non_secret_fields_only(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + "/ai-config.json"
            result = set_preferences(
                "openai",
                {
                    "enabled": True,
                    "default_model": "gpt-4o-mini",
                    "notes": "dev key",
                },
                path=path,
            )
            self.assertTrue(result.get("ok"))
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
            self.assertNotIn("sk-", raw)
            data = json.loads(raw)
            prefs = data["providers"]["openai"]
            self.assertTrue(prefs["enabled"])
            self.assertEqual(prefs["default_model"], "gpt-4o-mini")

    def test_set_preferences_rejects_api_key_in_json(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + "/ai-config.json"
            result = set_preferences("openai", {"api_key": "sk-secret"}, path=path)
            self.assertFalse(result.get("ok"))
            self.assertIn("secret", (result.get("detail") or "").lower())
            self.assertFalse(__import__("os").path.exists(path))

    def test_default_config_path_not_touched_by_tests(self) -> None:
        self.assertIn("pro-terminal-setup", DEFAULT_CONFIG_PATH)
        self.assertTrue(DEFAULT_CONFIG_PATH.endswith("ai-config.json"))


class TestCredentials(unittest.TestCase):
    def test_set_secret_without_store_returns_unavailable(self) -> None:
        with mock.patch.dict(sys.modules, {"ai.security": None}):
            # Force re-import path: patch _get_store via credentials module
            from ai.providers import credentials as cred_mod

            with mock.patch.object(cred_mod, "_get_store", return_value=None):
                result = cred_mod.set_secret("openai", "api_key", "sk-test")
            self.assertFalse(result.get("ok"))
            self.assertEqual(result.get("detail"), "credential store unavailable")

    def test_set_secret_delegates_to_store(self) -> None:
        fake_store = mock.Mock()
        fake_store.set_secret.return_value = {"ok": True, "detail": "stored"}
        from ai.providers import credentials as cred_mod

        with mock.patch.object(cred_mod, "_get_store", return_value=fake_store):
            result = set_secret("openai", "api_key", "sk-test")
        fake_store.set_secret.assert_called_once_with("openai", "api_key", "sk-test")
        self.assertTrue(result.get("ok"))

    def test_get_secret_configured_without_printing_value_in_status(self) -> None:
        fake_store = mock.Mock()
        fake_store.get_secret.return_value = {"ok": True, "value": "sk-hidden"}
        from ai.providers import credentials as cred_mod

        with mock.patch.object(cred_mod, "_get_store", return_value=fake_store):
            st = status("openai")
        self.assertTrue(st.get("configured"))
        self.assertNotIn("sk-hidden", json.dumps(st))


class TestStatus(unittest.TestCase):
    def test_cloud_not_configured_when_store_missing(self) -> None:
        from ai.providers import credentials as cred_mod

        with mock.patch.object(cred_mod, "_get_store", return_value=None):
            st = status("anthropic")
        self.assertFalse(st.get("configured"))
        self.assertEqual(st.get("kind"), "cloud")

    def test_local_status_uses_reachable(self) -> None:
        with mock.patch("ai.providers.provider_status.tcp_reachable", return_value=True):
            st = status("ollama")
        self.assertTrue(st.get("reachable"))
        self.assertEqual(st.get("base_url"), "http://127.0.0.1:11434")

    def test_tcp_reachable_refuses_non_localhost(self) -> None:
        self.assertFalse(tcp_reachable("http://example.com:11434"))

    def test_status_unknown_provider(self) -> None:
        st = status("unknown")
        self.assertFalse(st.get("ok"))


class TestSecurityModuleIntegration(unittest.TestCase):
    def test_delete_secret_via_store(self) -> None:
        fake_store = mock.Mock()
        fake_store.delete_secret.return_value = {"ok": True}
        from ai.providers import credentials as cred_mod

        with mock.patch.object(cred_mod, "_get_store", return_value=fake_store):
            result = delete_secret("google", "api_key")
        self.assertTrue(result.get("ok"))
        fake_store.delete_secret.assert_called_once_with("google", "api_key")

    def test_get_secret_via_store(self) -> None:
        fake_store = mock.Mock()
        fake_store.get_secret.return_value = {"ok": True, "value": "x"}
        from ai.providers import credentials as cred_mod

        with mock.patch.object(cred_mod, "_get_store", return_value=None):
            result = get_secret("google", "api_key")
        self.assertFalse(result.get("ok"))

        with mock.patch.object(cred_mod, "_get_store", return_value=fake_store):
            result = get_secret("google", "api_key")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("value"), "x")


if __name__ == "__main__":
    unittest.main()
