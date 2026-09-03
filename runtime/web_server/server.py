#!/usr/bin/env python3
"""Read-only loopback web server for the built Stremio TV interface."""

from __future__ import annotations

import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path


DEFAULT_ROOT = Path("/usr/share/stremio-vero/web")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/.stremio-vero/health":
            body = json.dumps({"status": "ready"}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self) -> None:
        if self.path == "/" or self.path.endswith("/index.html"):
            self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"stremio-web: {format % args}")


def serve(root: Path, bind: str, port: int) -> None:
    if bind not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("refusing non-loopback bind address")
    if root.is_symlink() or not (root / "index.html").is_file():
        raise SystemExit(f"Stremio Web build is missing: {root}")
    server = ThreadingHTTPServer((bind, port), partial(Handler, directory=str(root)))
    print(f"Stremio Web listening on http://{bind}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.root, args.bind, args.port)


if __name__ == "__main__":
    main()
