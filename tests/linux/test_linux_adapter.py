"""Linux adapter tests (dry-run only; no sudo execution on developer host)."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from ai.adapters import linux as linux_adapter
from ai.core.catalog import load_catalog


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LinuxAdapterDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.linux_host = {"os": "linux", "distro": "ubuntu"}
        self.fedora_host = {"os": "linux", "distro": "fedora"}
        self.macos_host = {"os": "macos", "distro": ""}

    def test_detect_non_linux_runtime(self) -> None:
        if sys.platform.startswith("linux"):
            self.skipTest("detect non-linux behavior requires non-Linux runtime")
        app = {"id": "git", "platforms": {"linux": {"method": "manual"}}}
        info = linux_adapter.detect(app, self.linux_host)
        self.assertFalse(info["installed"])

    def test_install_git_dry_run_ubuntu_plans_apt(self) -> None:
        app = {"id": "git", "platforms": {"linux": {"method": "manual"}}}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, self.linux_host, dry_run=True)
            run_mock.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "dry-run")
        self.assertIn("apt-get install", result["detail"])
        self.assertIn("git", result["detail"])

    def test_install_git_dry_run_fedora_plans_dnf(self) -> None:
        app = {"id": "git", "platforms": {"linux": {"method": "manual"}}}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, self.fedora_host, dry_run=True)
            run_mock.assert_not_called()
        self.assertIn("dnf install", result["detail"])

    def test_install_unknown_distro_manual_limitation(self) -> None:
        host = {"os": "linux", "distro": "arch"}
        app = {"id": "git", "platforms": {"linux": {"method": "manual", "limitation": "arch manual"}}}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, host, dry_run=True)
            run_mock.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertIn("arch manual", result["detail"])

    def test_ollama_script_dry_run_returns_curl_pipe_sh(self) -> None:
        app = {
            "id": "ollama",
            "platforms": {
                "linux": {
                    "method": "script",
                    "package": "https://ollama.com/install.sh",
                }
            },
        }
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, self.linux_host, dry_run=True)
            run_mock.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertIn("curl -fsSL https://ollama.com/install.sh | sh", result["detail"])

    def test_ollama_script_real_without_opt_in_blocks(self) -> None:
        app = {
            "id": "ollama",
            "platforms": {
                "linux": {
                    "method": "script",
                    "package": "https://ollama.com/install.sh",
                }
            },
        }
        env = {k: v for k, v in os.environ.items() if k != linux_adapter.SCRIPT_OPT_IN_ENV}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            with mock.patch.dict(os.environ, env, clear=True):
                result = linux_adapter.install(app, self.linux_host, dry_run=False)
            run_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertIn(linux_adapter.SCRIPT_OPT_IN_ENV, result["detail"])

    def test_cursor_manual_dry_run(self) -> None:
        app = {
            "id": "cursor",
            "official_url": "https://cursor.com",
            "platforms": {
                "linux": {
                    "method": "manual",
                    "limitation": "Download vendor package",
                }
            },
        }
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, self.linux_host, dry_run=True)
            run_mock.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertIn("manual:", result["detail"])
        self.assertIn("https://cursor.com", result["detail"])

    def test_host_not_linux_skipped(self) -> None:
        app = {"id": "git", "platforms": {"linux": {"method": "manual"}}}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            result = linux_adapter.install(app, self.macos_host, dry_run=True)
            run_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result["skipped"])

    def test_update_uninstall_repair_dry_run_no_subprocess(self) -> None:
        app = {"id": "python", "platforms": {"linux": {"method": "manual"}}}
        with mock.patch.object(linux_adapter.subprocess, "run") as run_mock:
            for fn in (linux_adapter.update, linux_adapter.uninstall, linux_adapter.repair):
                result = fn(app, self.linux_host, dry_run=True)
                self.assertTrue(result["ok"], msg=fn.__name__)
                self.assertEqual(result["action"], "dry-run")
            run_mock.assert_not_called()

    def test_linux_yaml_covers_catalog_ids(self) -> None:
        catalog = load_catalog(_repo_root())
        overlay_path = os.path.join(_repo_root(), "ai", "catalog", "sources", "linux.yaml")
        self.assertTrue(os.path.isfile(overlay_path))
        expected = {
            "chatgpt",
            "claude",
            "gemini",
            "copilot",
            "cursor",
            "lm-studio",
            "perplexity",
            "opencode",
            "cline",
            "ollama",
            "vscode",
            "continue",
            "aider",
            "open-webui",
            "gh",
            "git",
            "python",
            "node",
            "codex",
            "claude-code",
            "gemini-cli",
        }
        apps = {str(a.get("id")): a for a in catalog.get("applications") or []}
        for app_id in expected:
            self.assertIn(app_id, apps)
            entry = (apps[app_id].get("platforms") or {}).get("linux") or {}
            self.assertNotEqual(str(entry.get("method") or ""), "pending")
            self.assertFalse(entry.get("verified"))


if __name__ == "__main__":
    unittest.main()
