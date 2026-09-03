from __future__ import annotations

from functools import partial
import importlib.util
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def load_server():
    path = ROOT / "runtime" / "web_server" / "server.py"
    spec = importlib.util.spec_from_file_location("stremio_vero_web_server", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WebServerTests(unittest.TestCase):
    def test_serves_build_and_health_on_loopback(self) -> None:
        module = load_server()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<title>Stremio for Vero 4K+</title>", encoding="utf-8")
            handler = partial(module.Handler, directory=str(root))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(base + "/", timeout=2) as response:
                    self.assertIn(b"Stremio for Vero 4K+", response.read())
                    self.assertEqual(response.headers["Cache-Control"], "no-cache")
                with urllib.request.urlopen(base + "/.stremio-vero/health", timeout=2) as response:
                    self.assertEqual(json.loads(response.read())["status"], "ready")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
