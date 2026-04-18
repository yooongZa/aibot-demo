"""Tiny development server for the marketing/test site under web/.

Serves clean URLs (/, /about, /demo, /products) by mapping each route to the
matching .html file, exposes /static/* for shared CSS/JS, and adds an
/api/products endpoint that returns Products.json so /products page can
render the live catalog.

Run:
    python serve_web.py             # http://localhost:8080
    PORT=3000 python serve_web.py   # custom port
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from data import load_products

WEB_DIR = Path(__file__).parent / "web"
STATIC_DIR = WEB_DIR / "static"

ROUTES = {
    "/": "index.html",
    "/about": "about.html",
    "/demo": "demo.html",
    "/products": "products.html",
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "NutrifyDemo/1.0"

    def log_message(self, format, *args):  # quieter logs
        print(f"[web] {self.address_string()} - {format % args}")

    def _send(self, status: int, body: bytes, content_type: str = "text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
            return
        ct = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self._send(HTTPStatus.OK, path.read_bytes(), ct)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/api/products":
            data = json.dumps(load_products(), ensure_ascii=False).encode("utf-8")
            self._send(HTTPStatus.OK, data, "application/json; charset=utf-8")
            return

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(STATIC_DIR / rel)
            return

        if path in ROUTES:
            self._serve_file(WEB_DIR / ROUTES[path])
            return

        # Fallback: try to serve as a raw file under web/
        candidate = WEB_DIR / path.lstrip("/")
        if candidate.exists() and candidate.is_file():
            self._serve_file(candidate)
            return

        self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"🌿 Nutrify demo site running at http://{host}:{port}")
    print("   Routes: /, /about, /demo, /products  ·  API: /api/products")
    print("   (Make sure `chainlit run app.py -w` is running on :8000 for the chat widget)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[web] shutting down")
        server.server_close()


if __name__ == "__main__":
    main()
