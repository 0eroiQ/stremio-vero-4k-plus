from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_verifier():
    path = ROOT / "scripts" / "verify_stremio_web_build.py"
    spec = importlib.util.spec_from_file_location("verify_stremio_web_build", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StremioWebBuildVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = load_verifier()

    def fixture(self, root: Path, commit: str) -> Path:
        build = root / "build"
        commit_root = build / commit
        for relative in (
            "scripts/main.js",
            "styles/main.css",
            "binaries/stremio_core_web_bg.wasm",
        ):
            path = commit_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
        (build / "index.html").write_text(
            f'<script src="{commit}/scripts/main.js"></script>'
            f'<link href="{commit}/styles/main.css">'
            f'<link href="{commit}/binaries/stremio_core_web_bg.wasm">',
            encoding="utf-8",
        )
        return build

    def test_accepts_only_the_pinned_commit_label(self) -> None:
        expected = "1" * 40
        with tempfile.TemporaryDirectory() as directory:
            build = self.fixture(Path(directory), expected)
            self.assertEqual(self.verifier.verify(build, expected), {expected})

    def test_rejects_parent_project_commit_label(self) -> None:
        expected = "1" * 40
        actual = "2" * 40
        with tempfile.TemporaryDirectory() as directory:
            build = self.fixture(Path(directory), actual)
            with self.assertRaisesRegex(ValueError, "expected"):
                self.verifier.verify(build, expected)


if __name__ == "__main__":
    unittest.main()
