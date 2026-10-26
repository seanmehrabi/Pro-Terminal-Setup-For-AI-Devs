"""Secret store command builders and backends (fake runner only)."""

from __future__ import annotations

import unittest
from unittest import mock

import ai.security.store as store


class TestAccountAndRedact(unittest.TestCase):
    def test_account_key_format(self) -> None:
        self.assertEqual(store.account_key("openai", "api_key"), "openai:api_key")

    def test_redact_masks_sk_prefix_and_pass_flag(self) -> None:
        raw = "failed sk-abcdefghijklmnopqrstuvwxyz1234567890 and -w my-secret-value"
        redacted = store.redact(raw)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz1234567890", redacted)
        self.assertNotIn("my-secret-value", redacted)
        self.assertIn("[REDACTED]", redacted)


class TestCommandBuilders(unittest.TestCase):
    def test_macos_commands(self) -> None:
        account = "openai:api_key"
        self.assertEqual(
            store.macos_add_command(account, "sekret"),
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                "pro-terminal-setup",
                "-a",
                account,
                "-w",
                "sekret",
            ],
        )
        self.assertEqual(
            store.macos_find_command(account),
            [
                "security",
                "find-generic-password",
                "-s",
                "pro-terminal-setup",
                "-a",
                account,
                "-w",
            ],
        )
        self.assertEqual(
            store.macos_delete_command(account),
            [
                "security",
                "delete-generic-password",
                "-s",
                "pro-terminal-setup",
                "-a",
                account,
            ],
        )

    def test_windows_commands(self) -> None:
        account = "anthropic:token"
        target = "pro-terminal-setup:anthropic:token"
        self.assertEqual(
            store.windows_set_command(account, "pw"),
            ["cmdkey", f"/generic:{target}", f"/user:{account}", "/pass:pw"],
        )
        self.assertEqual(
            store.windows_delete_command(account),
            ["cmdkey", f"/delete:{target}"],
        )

    def test_linux_commands(self) -> None:
        account = "gemini:key"
        self.assertEqual(
            store.linux_store_command(account)[0:2],
            ["secret-tool", "store"],
        )
        self.assertIn("pro-terminal-setup", store.linux_lookup_command(account))
        self.assertIn("clear", store.linux_clear_command(account))


class TestMacOSStoreWithFakeRunner(unittest.TestCase):
    def test_set_get_delete_round_trip(self) -> None:
        vault: dict[str, str] = {}

        def fake_runner(cmd: list[str], *, input: str | None = None) -> tuple[int, str, str]:
            if cmd[0] == "security" and cmd[1] == "add-generic-password":
                account = cmd[cmd.index("-a") + 1]
                value = cmd[cmd.index("-w") + 1]
                vault[account] = value
                return 0, "", ""
            if cmd[0] == "security" and cmd[1] == "find-generic-password":
                account = cmd[cmd.index("-a") + 1]
                if account in vault:
                    return 0, vault[account] + "\n", ""
                return 44, "", "not found"
            if cmd[0] == "security" and cmd[1] == "delete-generic-password":
                account = cmd[cmd.index("-a") + 1]
                vault.pop(account, None)
                return 0, "", ""
            return 1, "", "unexpected"

        with mock.patch.object(store, "_os_kind", return_value="macos"):
            self.assertEqual(store.backend_name(), "macos-keychain")
            put = store.set_secret("openai", "api_key", "super-secret", runner=fake_runner)
            self.assertTrue(put["ok"])
            got = store.get_secret("openai", "api_key", runner=fake_runner)
            self.assertTrue(got["ok"])
            self.assertEqual(got["value"], "super-secret")
            deleted = store.delete_secret("openai", "api_key", runner=fake_runner)
            self.assertTrue(deleted["ok"])
            missing = store.get_secret("openai", "api_key", runner=fake_runner)
            self.assertFalse(missing["ok"])


class TestWindowsLimitedGet(unittest.TestCase):
    def test_get_refuses_cmdkey_read(self) -> None:
        with mock.patch.object(store, "_os_kind", return_value="windows"):
            self.assertEqual(store.backend_name(), "windows-cmdkey-limited")
            result = store.get_secret("openai", "api_key", runner=lambda *_a, **_k: (0, "", ""))
            self.assertFalse(result["ok"])
            self.assertIn("win32", result["detail"].lower())

    def test_set_invokes_cmdkey(self) -> None:
        seen: list[list[str]] = []

        def fake_runner(cmd: list[str], *, input: str | None = None) -> tuple[int, str, str]:
            seen.append(cmd)
            return 0, "", ""

        with mock.patch.object(store, "_os_kind", return_value="windows"):
            store.set_secret("p", "n", "v", runner=fake_runner)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], "cmdkey")


class TestLinuxSecretTool(unittest.TestCase):
    def test_missing_secret_tool_refuses_store(self) -> None:
        with mock.patch.object(store, "_os_kind", return_value="linux"):
            with mock.patch.object(store.shutil, "which", return_value=None):
                result = store.set_secret("openai", "api_key", "x")
        self.assertFalse(result["ok"])
        self.assertIn("libsecret-tools", result["detail"])

    def test_store_uses_stdin(self) -> None:
        captured: dict[str, str] = {}

        def fake_runner(cmd: list[str], *, input: str | None = None) -> tuple[int, str, str]:
            if cmd[0] == "secret-tool" and cmd[1] == "store":
                account = cmd[-1]
                captured[account] = input or ""
                return 0, "", ""
            if cmd[0] == "secret-tool" and cmd[1] == "lookup":
                account = cmd[-1]
                if account in captured:
                    return 0, captured[account], ""
                return 1, "", "not found"
            if cmd[0] == "secret-tool" and cmd[1] == "clear":
                captured.pop(cmd[-1], None)
                return 0, "", ""
            return 1, "", "bad"

        with mock.patch.object(store, "_os_kind", return_value="linux"):
            with mock.patch.object(store.shutil, "which", return_value="/usr/bin/secret-tool"):
                store.set_secret("p", "n", "stdin-val", runner=fake_runner)
                got = store.get_secret("p", "n", runner=fake_runner)
                self.assertTrue(got["ok"])
                self.assertEqual(got["value"], "stdin-val")


class TestUnsupportedPlatform(unittest.TestCase):
    def test_no_plaintext_on_unknown_os(self) -> None:
        with mock.patch.object(store, "_os_kind", return_value="unsupported"):
            self.assertEqual(store.backend_name(), "unsupported")
            for fn in (store.set_secret, store.get_secret, store.delete_secret):
                result = fn("p", "n", "v") if fn is store.set_secret else fn("p", "n")
                self.assertFalse(result["ok"])
                self.assertIn("plaintext", result["detail"].lower())


if __name__ == "__main__":
    unittest.main()
