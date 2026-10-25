"""Windows adapter planning and dry-run behavior (host-agnostic tests)."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from ai.adapters import windows
from ai.core.platform import detect_host


class TestWindowsPlan(unittest.TestCase):
    def test_dry_run_install_on_mac_does_not_invoke_subprocess(self) -> None:
        host = detect_host()
        self.assertNotEqual(host.get("os"), "windows")

        app = {
            "id": "git",
            "platforms": {
                "windows": {
                    "method": "winget",
                    "package": "Git.Git",
                    "official_url": "https://git-scm.com",
                }
            },
        }

        with mock.patch.object(subprocess, "run") as proc_run:
            with mock.patch.object(windows, "_run_command") as runner:
                result = windows.install(app, host, dry_run=True)
                proc_run.assert_not_called()
                runner.assert_not_called()

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("action"), "dry-run")
        self.assertIn("winget", result.get("detail") or "")

    def test_known_app_dict_detail_contains_winget_when_package_set(self) -> None:
        app = {
            "id": "cursor",
            "platforms": {
                "windows": {
                    "method": "winget",
                    "package": "Anysphere.Cursor",
                    "official_url": "https://cursor.com",
                }
            },
        }
        host = {"os": "macos", "winget": False}

        with mock.patch.object(windows, "_run_command") as runner:
            result = windows.install(app, host, dry_run=True)
            runner.assert_not_called()

        detail = result.get("detail") or ""
        self.assertIn("winget", detail.lower())
        self.assertIn("Anysphere.Cursor", detail)

    def test_detect_non_windows_skipped(self) -> None:
        app = {"platforms": {"windows": {"method": "winget", "package": "Git.Git"}}}
        info = windows.detect(app, {"os": "macos"})
        self.assertFalse(info.get("installed"))
        self.assertEqual(info.get("method"), "skipped-not-windows")

    def test_install_non_windows_without_dry_run_requires_windows(self) -> None:
        app = {"platforms": {"windows": {"method": "winget", "package": "Git.Git"}}}
        with mock.patch.object(windows, "_run_command") as runner:
            result = windows.install(app, {"os": "linux"}, dry_run=False)
            runner.assert_not_called()
        self.assertFalse(result.get("ok"))
        self.assertIn("Windows host required", result.get("detail") or "")


if __name__ == "__main__":
    unittest.main()
