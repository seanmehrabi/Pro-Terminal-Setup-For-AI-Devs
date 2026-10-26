"""Model recommendations and endpoint probes (mocked; no network in tests)."""

from __future__ import annotations

import importlib
import unittest
from unittest import mock

recommend_module = importlib.import_module("ai.models.recommend")
from ai.models.endpoints import endpoints_status, tcp_reachable
from ai.models.gpu import gpu_note
from ai.models.recommend import recommend


def _gb(n: float) -> int:
    return int(n * 1024**3)


class TestRecommend(unittest.TestCase):
    def test_under_8gb_tiny_only(self) -> None:
        rec = recommend({"arch": "arm64", "memory_bytes": _gb(6)})
        self.assertEqual(rec["memory_gb"], 6.0)
        self.assertEqual(rec["arch"], "arm64")
        ids = {s["id"] for s in rec["suggestions"]}
        self.assertIn("phi3:mini", ids)
        self.assertTrue(all("limited" in s["note"].lower() or "tiny" in s["note"].lower() for s in rec["suggestions"][:3]))
        self.assertEqual({s["runtime"] for s in rec["suggestions"]}, {"ollama", "lm-studio"})

    def test_8_to_16gb_seven_eight_b_class(self) -> None:
        rec = recommend({"arch": "x86_64", "memory_bytes": _gb(12)})
        ids = {s["id"] for s in rec["suggestions"]}
        self.assertIn("llama3.1:8b-instruct-q4_K_M", ids)
        self.assertIn("mistral:7b-instruct-q4_K_M", ids)
        self.assertNotIn("qwen2.5:14b-instruct-q4_K_M", ids)

    def test_16_to_32gb_fourteen_b_class(self) -> None:
        rec = recommend({"arch": "arm64", "memory_bytes": _gb(24)})
        ids = {s["id"] for s in rec["suggestions"]}
        self.assertIn("qwen2.5:14b-instruct-q4_K_M", ids)
        self.assertNotIn("llama3.1:70b-instruct-q4_K_M", ids)

    def test_32gb_plus_optional_larger(self) -> None:
        rec = recommend({"arch": "arm64", "memory_bytes": _gb(64)})
        ids = {s["id"] for s in rec["suggestions"]}
        self.assertIn("qwen2.5:32b-instruct-q4_K_M", ids)
        self.assertIn("llama3.1:70b-instruct-q4_K_M", ids)

    def test_uses_host_memory_bytes(self) -> None:
        with mock.patch("ai.models.memory._detect_system_memory_bytes", return_value=_gb(999)):
            rec = recommend({"memory_bytes": _gb(10)})
        self.assertEqual(rec["memory_gb"], 10.0)

    def test_gpu_from_gpu_note(self) -> None:
        with mock.patch.object(recommend_module, "gpu_note", return_value="Test GPU"):
            rec = recommend({"memory_bytes": _gb(16), "arch": "arm64"})
        self.assertEqual(rec["gpu"], "Test GPU")

    def test_suggestion_shape(self) -> None:
        rec = recommend({"memory_bytes": _gb(16), "arch": "arm64"})
        for s in rec["suggestions"]:
            self.assertIn(s["runtime"], ("ollama", "lm-studio"))
            self.assertIsInstance(s["id"], str)
            self.assertIsInstance(s["size_gb"], (int, float))
            self.assertIsInstance(s["note"], str)


class TestEndpointsStatus(unittest.TestCase):
    def test_both_closed(self) -> None:
        with mock.patch("ai.models.endpoints.tcp_reachable", return_value=False):
            status = endpoints_status()
        self.assertFalse(status["ollama"]["tcp_open"])
        self.assertFalse(status["lm_studio"]["tcp_open"])
        self.assertIsNone(status["ollama"]["http_ok"])
        self.assertIsNone(status["lm_studio"]["http_ok"])

    def test_tcp_open_http_checked(self) -> None:
        def fake_tcp(host: str, port: int, timeout: float) -> bool:
            return port == 11434

        with mock.patch("ai.models.endpoints.tcp_reachable", side_effect=fake_tcp):
            with mock.patch("ai.models.endpoints.http_reachable", return_value=True) as http_mock:
                status = endpoints_status()
        self.assertTrue(status["ollama"]["tcp_open"])
        self.assertTrue(status["ollama"]["http_ok"])
        self.assertFalse(status["lm_studio"]["tcp_open"])
        http_mock.assert_called_once()

    def test_tcp_reachable_uses_socket(self) -> None:
        with mock.patch("socket.create_connection") as conn:
            conn.return_value.__enter__ = mock.Mock(return_value=None)
            conn.return_value.__exit__ = mock.Mock(return_value=False)
            self.assertTrue(tcp_reachable("127.0.0.1", 11434, 0.3))
        conn.assert_called_once_with(("127.0.0.1", 11434), timeout=0.3)


class TestGpuNote(unittest.TestCase):
    def test_non_darwin_returns_none(self) -> None:
        with mock.patch("sys.platform", "linux"):
            self.assertIsNone(gpu_note())

    def test_darwin_parses_chipset(self) -> None:
        stdout = "Chipset Model: Example GPU 8 GB\n"
        with mock.patch("sys.platform", "darwin"):
            with mock.patch(
                "subprocess.run",
                return_value=mock.Mock(returncode=0, stdout=stdout),
            ):
                self.assertEqual(gpu_note(), "Example GPU 8 GB")

    def test_darwin_slow_or_fail_returns_none(self) -> None:
        with mock.patch("sys.platform", "darwin"):
            with mock.patch("subprocess.run", side_effect=OSError("timeout")):
                self.assertIsNone(gpu_note())


if __name__ == "__main__":
    unittest.main()
