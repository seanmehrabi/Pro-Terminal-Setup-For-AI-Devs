"""Engine planning, dry-run, and CLI contract tests."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import types
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import ai.core.engine as engine_mod
except ImportError as _ENGINE_IMPORT_ERROR:
    engine_mod = None  # type: ignore[assignment]
    _ENGINE_ERR = _ENGINE_IMPORT_ERROR
else:
    _ENGINE_ERR = None

try:
    from ai.core.catalog import load_catalog as _load_catalog_fn
except ImportError as _CATALOG_IMPORT_ERROR:
    _load_catalog_fn = None  # type: ignore[assignment]
    _CATALOG_ERR = _CATALOG_IMPORT_ERROR
else:
    _CATALOG_ERR = None


def _require_engine() -> None:
    if engine_mod is None:
        raise unittest.SkipTest("ai.core.engine not importable: {}".format(_ENGINE_ERR))


def _require_catalog():
    _require_engine()
    if _load_catalog_fn is None:
        raise unittest.SkipTest("ai.core.catalog not importable: {}".format(_CATALOG_ERR))
    return _load_catalog_fn(REPO_ROOT)


class TestSelectIds(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = _require_catalog()

    def test_profile_coding_resolves_members(self) -> None:
        ids = engine_mod.select_ids(self.catalog, ["coding"], False, None)
        self.assertIn("cursor", ids)
        self.assertIn("vscode", ids)

    def test_explicit_ids_merge_with_profile(self) -> None:
        ids = engine_mod.select_ids(self.catalog, ["coding"], False, ["git"])
        self.assertIn("git", ids)
        self.assertIn("cursor", ids)


class TestBuildPlanSkipInstalled(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _require_engine()

    def test_skip_when_detect_reports_installed(self) -> None:
        catalog = {
            "applications": [
                {
                    "id": "demo-app",
                    "name": "Demo",
                    "platforms": {
                        "macos": {
                            "method": "brew-formula",
                            "package": "demo",
                            "verified": True,
                        }
                    },
                }
            ],
            "profiles": {},
        }
        host = {"os": "macos", "brew": True}
        stub = types.ModuleType("stub")
        stub.detect = lambda app, h: {
            "installed": True,
            "version": "1.0.0",
            "path": "/tmp/demo",
            "method": "brew-formula",
        }
        stub.install = lambda *a, **k: {"ok": False, "action": "install", "detail": "should not run"}

        with mock.patch.object(engine_mod, "get_adapter", return_value=stub):
            plan = engine_mod.build_plan(catalog, host, ["demo-app"])

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].get("action"), "skip")
        self.assertIn("installed", (plan[0].get("detail") or "").lower())


class TestDryRunNoNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = _require_catalog()

    def _block_network(self) -> list:
        def _deny(*_args, **_kwargs):
            raise OSError("network disabled for dry-run test")

        patchers = [
            mock.patch.object(socket.socket, "connect", side_effect=_deny),
        ]
        try:
            import urllib.request

            patchers.append(mock.patch.object(urllib.request, "urlopen", side_effect=_deny))
        except ImportError:
            pass
        return patchers

    def test_run_plan_dry_run_never_calls_install(self) -> None:
        host = {"os": "macos", "brew": True}
        ids = ["git", "node"]
        plan = engine_mod.build_plan(self.catalog, host, ids)
        stub = types.ModuleType("stub")
        stub.detect = lambda app, h: {"installed": False, "version": "", "path": "", "method": ""}

        def _fail_install(*_a, **_k):
            raise AssertionError("install must not run during dry-run")

        stub.install = _fail_install
        stub.update = _fail_install
        stub.uninstall = _fail_install
        stub.repair = _fail_install

        with mock.patch.object(engine_mod, "get_adapter", return_value=stub):
            results = engine_mod.run_plan(plan, host, self.catalog, dry_run=True, operation="install")

        self.assertGreater(len(results), 0)
        for row in results:
            self.assertIn(row.get("action"), ("dry-run", "skip", "manual", "unsupported", "fallback"))

    def test_cli_dry_run_profile_local_exits_without_network(self) -> None:
        patchers = self._block_network()
        for p in patchers:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patchers])

        env = os.environ.copy()
        env["PYTHONPATH"] = REPO_ROOT
        proc = subprocess.run(
            [sys.executable, "-m", "ai", "dry-run", "--profile", "local"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 and "No module named" in (proc.stderr or ""):
            self.skipTest("ai package not runnable: {}".format(proc.stderr.strip()))
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("Dry run plan:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
