"""Catalog loading and profile contract tests."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _import_catalog():
    try:
        from ai.core.catalog import load_catalog

        return load_catalog
    except ImportError as exc:
        return exc


class TestCatalogLoad(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        loader = _import_catalog()
        if isinstance(loader, BaseException):
            raise unittest.SkipTest("ai.core.catalog not importable: {}".format(loader))
        cls.load_catalog = loader
        cls.catalog = cls.load_catalog(REPO_ROOT)

    def test_load_returns_applications_and_profiles(self) -> None:
        self.assertIn("applications", self.catalog)
        self.assertIn("profiles", self.catalog)
        apps = self.catalog.get("applications") or []
        self.assertIsInstance(apps, list)
        self.assertGreater(len(apps), 0)
        ids = {a.get("id") for a in apps if isinstance(a, dict)}
        self.assertIn("cursor", ids)
        self.assertIn("git", ids)

    def test_required_profiles_exist(self) -> None:
        profiles = self.catalog.get("profiles") or {}
        for name in ("coding", "chat", "agents", "local"):
            self.assertIn(name, profiles, "missing profile {}".format(name))
            self.assertIsInstance(profiles[name], list)
            self.assertGreater(len(profiles[name]), 0, "profile {} is empty".format(name))

    def test_profile_members_reference_catalog_apps(self) -> None:
        apps = self.catalog.get("applications") or []
        known = {str(a.get("id")) for a in apps if a.get("id")}
        profiles = self.catalog.get("profiles") or {}
        for name, members in profiles.items():
            for app_id in members:
                self.assertIn(
                    str(app_id),
                    known,
                    "profile {} references unknown app id {}".format(name, app_id),
                )

    def test_platform_overlays_merge_when_present(self) -> None:
        apps = self.catalog.get("applications") or []
        git = next((a for a in apps if a.get("id") == "git"), None)
        self.assertIsNotNone(git)
        platforms = (git or {}).get("platforms") or {}
        for os_name in ("macos", "linux", "windows"):
            entry = platforms.get(os_name)
            if entry is None:
                continue
            self.assertIn("method", entry)


class TestListCli(unittest.TestCase):
    def test_python_m_ai_list_exits_zero(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = REPO_ROOT
        proc = subprocess.run(
            [sys.executable, "-m", "ai", "list"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 and "No module named" in (proc.stderr or ""):
            self.skipTest("ai package not runnable: {}".format(proc.stderr.strip()))
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("Profiles:", proc.stdout)
        for profile in ("coding", "chat", "agents", "local"):
            self.assertIn(profile, proc.stdout)


if __name__ == "__main__":
    unittest.main()
