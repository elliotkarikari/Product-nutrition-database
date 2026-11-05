"""ShelfScale assessment API (prototype, standard library only).

Endpoints:
    GET  /health          -> {"status": "ok", "model": "uk-npm-2004/05"}
    POST /v1/assess       -> one product  (see service.assess_product)
    POST /v1/assess/bulk  -> many products (see service.assess_bulk)
    POST /v1/lookup       -> one CoFID food by code or exact name (see cofid_assess)
    POST /v1/lookup/bulk  -> many lookups (see cofid_assess.lookup_bulk)

Run locally:
    PYTHONPATH=src python3 -m shelfscale.api --port 8765

This is a working prototype of the API contract in docs/API.md, not a
production deployment: authentication, rate limits, TLS and asynchronous
bulk jobs are specified there and are added before any public hosting.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .cofid_assess import lookup_and_assess, lookup_bulk
from .service import MODEL_ID, assess_bulk, assess_product

ROUTES = {
    "/v1/assess": assess_product,
    "/v1/assess/bulk": assess_bulk,
    "/v1/lookup": lookup_and_assess,
    "/v1/lookup/bulk": lookup_bulk,
}

MAX_BODY_BYTES = 5_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = "ShelfScale/0.1"

    def _send_json(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "model": MODEL_ID})
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ROUTES:
            self._send_json(404, {"error": "Not found."})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Request body missing or too large."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return
        try:
            self._send_json(200, ROUTES[self.path](payload))
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:  # keep test output clean
        pass


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ShelfScale API listening on http://{host}:{port} (model {MODEL_ID})")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="ShelfScale assessment API prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
