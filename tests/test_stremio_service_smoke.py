from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_smoke():
    path = ROOT / "scripts" / "smoke_stremio_service.py"
    spec = importlib.util.spec_from_file_location("smoke_stremio_service", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(307)
        self.send_header("Location", "http://127.0.0.1:1/not-running")
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


class RunningProcess:
    returncode = None

    @staticmethod
    def poll():
        return None


class StremioServiceSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = load_smoke()

    def test_server_redirect_is_accepted_without_following_web_ui(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            self.assertEqual(self.smoke.wait_for_http(RunningProcess(), 2, url), 307)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
