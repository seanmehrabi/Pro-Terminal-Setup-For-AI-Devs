"""Unit tests for ai.adapters.macos detect/install (dry-run)."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from ai.core.platform import detect_host
except ImportError:  # pragma: no cover - core optional in partial checkouts
    detect_host = None  # type: ignore[assignment,misc]

from ai.adapters import macos


class TestDetectHost(unittest.TestCase):
    @unittest.skipIf(detect_host is None, "ai.core.platform not available in this checkout")
    def test_detect_host_macos(self) -> None:
        host = detect_host()
        self.assertEqual(host.get("os"), "macos")
        self.assertTrue(host.get("arch"))
        self.assertGreater(host.get("memory_bytes", 0), 0)
        self.assertGreater(host.get("disk_free_bytes", 0), 0)


class TestMacosDetect(unittest.TestCase):
    def _host(self) -> dict:
        if detect_host is not None:
            return detect_host()
        return {
            "os": "macos",
            "arch": "arm64",
            "home": os.path.expanduser("~"),
            "brew": os.path.isfile("/opt/homebrew/bin/brew"),
            "brew_path": "/opt/homebrew/bin/brew",
        }

    def test_detect_iterm_or_cursor_app(self) -> None:
        host = self._host()
        app_name = "iTerm.app"
        if not os.path.isdir("/Applications/iTerm.app"):
            app_name = "Cursor.app"
        self.assertTrue(os.path.isdir(os.path.join("/Applications", app_name)), "need iTerm or Cursor")
        app = {
            "id": "probe",
            "platforms": {
                "macos": {
                    "method": "manual",
                    "package": "",
                    "detect_app": app_name,
                    "detect_cmd": "",
                    "verified": False,
                }
            },
        }
        result = macos.detect(app, host)
        self.assertTrue(result["installed"])
        self.assertIn(".app", result["path"] or "")

    def test_platform_block_top_level_shape(self) -> None:
        host = self._host()
        app = {
            "method": "brew-formula",
            "package": "gh",
            "detect_cmd": "gh --version",
            "verified": True,
        }
        result = macos.detect(app, host)
        self.assertIn("installed", result)


class TestDryRunInstall(unittest.TestCase):
    def test_dry_run_does_not_invoke_subprocess(self) -> None:
        host = {
            "os": "macos",
            "home": os.path.expanduser("~"),
            "brew_path": "/opt/homebrew/bin/brew",
        }
        app = {
            "platforms": {
                "macos": {
                    "method": "brew-cask",
                    "package": "chatgpt",
                    "detect_app": "ChatGPT.app",
                    "verified": True,
                }
            }
        }

        with mock.patch.object(macos, "_runner") as runner:
            runner.side_effect = AssertionError("subprocess must not run when dry_run=True")
            with mock.patch.object(macos, "detect", return_value={"installed": False, "version": None, "path": None, "method": ""}):
                out = macos.install(app, host, dry_run=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["action"], "dry-run")
        self.assertIn("brew install --cask chatgpt", out["detail"])
        self.assertFalse(out["skipped"])

    def test_skip_when_installed_dry_run(self) -> None:
        host = {"os": "macos", "brew_path": "/opt/homebrew/bin/brew"}
        app = {
            "platforms": {
                "macos": {
                    "method": "brew-cask",
                    "package": "cursor",
                    "verified": True,
                }
            }
        }
        with mock.patch.object(macos, "detect", return_value={"installed": True, "version": "1.0", "path": "/Applications/Cursor.app", "method": "brew-cask"}):
            out = macos.install(app, host, dry_run=True)
        self.assertTrue(out["skipped"])
        self.assertEqual(out["action"], "skip")


class TestLiveCatalogDetection(unittest.TestCase):
    """Print installed state for macos.yaml entries (detect only, no network)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.host = detect_host() if detect_host else {
            "os": "macos",
            "home": os.path.expanduser("~"),
            "brew_path": "/opt/homebrew/bin/brew",
        }
        cls.rows = []
        yaml_path = os.path.join(ROOT, "ai", "catalog", "sources", "macos.yaml")
        if not os.path.isfile(yaml_path):
            cls.entries = {}
            return
        from ai.core.yaml_lite import parse

        with open(yaml_path, "r", encoding="utf-8") as fh:
            cls.entries = parse(fh.read())
        for app_id, cfg in cls.entries.items():
            app = {"id": app_id, "platforms": {"macos": cfg}}
            info = macos.detect(app, cls.host)
            cls.rows.append((app_id, info.get("installed"), info.get("version")))

    def test_live_detection_runs(self) -> None:
        self.assertIsInstance(self.rows, list)
        print("\nLive macOS catalog detection:")
        print("{:<16} {:<10} {}".format("id", "installed", "version"))
        for app_id, installed, version in self.rows:
            print("{:<16} {!s:<10} {}".format(app_id, installed, version or ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
