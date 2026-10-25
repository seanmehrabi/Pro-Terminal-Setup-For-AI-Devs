"""Coding-agent registry probes (mocked; no real installs)."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

import ai.agents.scan as scan_mod
from ai.agents import list_agents, probe, render_report


class TestAgentsRegistry(unittest.TestCase):
    def test_list_agents_returns_seven_known_ids(self) -> None:
        agents = list_agents()
        ids = [a["id"] for a in agents]
        self.assertEqual(
            ids,
            [
                "codex",
                "claude-code",
                "gemini-cli",
                "opencode",
                "cline",
                "copilot",
                "cursor",
            ],
        )

    def test_cline_marked_unverified(self) -> None:
        cline = next(a for a in list_agents() if a["id"] == "cline")
        self.assertFalse(cline["verified"])
        self.assertIn("unverified", (cline.get("note") or "").lower())

    def test_list_agents_returns_copies(self) -> None:
        first = list_agents()
        first[0]["note"] = "mutated"
        second = list_agents()
        self.assertNotEqual(first[0]["note"], second[0]["note"])


class TestAgentsProbe(unittest.TestCase):
    def test_cli_probe_uses_which_and_version(self) -> None:
        def fake_which(name: str) -> str:
            if name == "codex":
                return "/usr/local/bin/codex"
            return ""

        with mock.patch.object(scan_mod, "_run_version", return_value="codex 1.0.0"):
            rows = probe(which_fn=fake_which)

        codex = next(r for r in rows if r["id"] == "codex")
        self.assertTrue(codex["installed"])
        self.assertEqual(codex["command"], "/usr/local/bin/codex")
        self.assertEqual(codex["version"], "codex 1.0.0")

    def test_vscode_extension_probe_when_code_missing(self) -> None:
        with mock.patch.object(scan_mod, "_list_vscode_extensions") as list_ext:
            rows = probe(which_fn=lambda _n: None)
            list_ext.assert_not_called()

        cline = next(r for r in rows if r["id"] == "cline")
        self.assertFalse(cline["installed"])
        self.assertFalse(cline["vscode_checked"])

    def test_vscode_extension_detects_installed_id(self) -> None:
        def fake_which(name: str) -> str:
            if name == "code":
                return "/usr/bin/code"
            return ""

        with mock.patch.object(
            scan_mod,
            "_list_vscode_extensions",
            return_value=["GitHub.copilot", "other.ext"],
        ):
            rows = probe(which_fn=fake_which)

        copilot = next(r for r in rows if r["id"] == "copilot")
        self.assertTrue(copilot["installed"])
        self.assertEqual(copilot["extension_id"], "GitHub.copilot")
        self.assertTrue(copilot["vscode_checked"])

    def test_desktop_cursor_from_app_path(self) -> None:
        with mock.patch.object(scan_mod.os.path, "exists", return_value=True):
            rows = probe(which_fn=lambda _n: None)
        cursor = next(r for r in rows if r["id"] == "cursor")
        self.assertTrue(cursor["installed"])

    def test_render_report_plain_text(self) -> None:
        probes = [
            {
                "id": "codex",
                "name": "Codex CLI",
                "kind": "cli",
                "verified": True,
                "note": "",
                "installed": True,
                "command": "/bin/codex",
                "version": "codex 1.0",
                "extension_id": "",
                "vscode_checked": False,
                "optional_cli_installed": False,
                "optional_cli_version": "",
            }
        ]
        text = render_report(probes)
        self.assertIn("Coding agents", text)
        self.assertIn("Codex CLI", text)
        self.assertIn("installed", text)
        self.assertIn("codex 1.0", text)

    def test_probe_never_calls_subprocess_install(self) -> None:
        def fake_which(name: str) -> str:
            if name in ("code", "codex"):
                return "/bin/" + name
            return ""

        with mock.patch.object(subprocess, "run") as proc_run:
            proc_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="GitHub.copilot\n",
                stderr="",
            )
            with mock.patch.object(scan_mod, "_run_version", return_value="v1"):
                probe(which_fn=fake_which)

        for call in proc_run.call_args_list:
            argv = call[0][0] if call[0] else call.kwargs.get("args", [])
            joined = " ".join(str(a) for a in argv).lower()
            self.assertNotIn("install", joined)
            self.assertNotIn("--install", joined)


if __name__ == "__main__":
    unittest.main()
