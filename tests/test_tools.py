from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SourceLockTests(unittest.TestCase):
    def test_source_lock_is_valid_json(self) -> None:
        data = json.loads((ROOT / "sources" / "sources.lock.json").read_text())
        self.assertEqual(data["schema"], 1)
        self.assertGreaterEqual(len(data["sources"]), 1)

    def test_every_binary_input_has_sha256(self) -> None:
        data = json.loads((ROOT / "sources" / "sources.lock.json").read_text())
        releases = [s for s in data["sources"] if s["revision_type"] == "release"]
        self.assertTrue(releases)
        self.assertTrue(all(len(source.get("sha256", "")) == 64 for source in releases))


class FetchSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fetch = load_script("fetch_verified")

    def test_only_official_download_hosts_are_allowed(self) -> None:
        self.assertEqual(
            self.fetch.safe_name("https://dl.strem.io/path/app.apk"), "app.apk"
        )
        with self.assertRaises(ValueError):
            self.fetch.safe_name("https://example.com/app.apk")

    def test_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "input"
            path.write_bytes(b"stremio-vero")
            self.assertEqual(
                self.fetch.digest(path),
                "4238de9419224e8813579ab4be59d04a09d3951f030beb87413828d66ed36e05",
            )


if __name__ == "__main__":
    unittest.main()
