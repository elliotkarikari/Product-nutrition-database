"""ShelfScale assessment API (prototype, standard library only).

Endpoints:
    GET  /health          -> {"status": "ok", "models": {"uk-npm-2004/05": "in force",
                                                  "uk-npm-2018": "shadow model, not in force"}}
    POST /v1/assess       -> one product  (see service.assess_product)
    POST /v1/assess/bulk  -> many products (see service.assess_bulk)
    POST /v1/lookup       -> one CoFID food by code or exact name (see cofid_assess)
    POST /v1/lookup/bulk  -> many lookups (see cofid_assess.lookup_bulk)

Run locally:
    PYTHONPATH=src python3 -m shelfscale.api --port 8765

This prototype is hosted on Railway. Authentication and rate limiting are
queued for hardening; asynchronous bulk jobs are specified but not implemented.
"""

from __future__ import annotations

import argparse
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .cofid_assess import lookup_and_assess, lookup_bulk
from .npm2018 import MODEL_ID as NPM2018_ID, STATUS as NPM2018_STATUS
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
        raw = json.dumps(body, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/health":
            self._send_json(200, {"status": "ok",
                                  "models": {MODEL_ID: "in force", NPM2018_ID: NPM2018_STATUS}})
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ROUTES:
            self._send_json(404, {"error": "Not found."})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._send_json(400, {"error": "Supply one numeric Content-Length; transfer encoding is unsupported."})
            return
        try:
            length = int(lengths[0])
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length."})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Request body missing or too large."})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete body")
            def reject_constant(value):
                raise ValueError(f"Non-finite JSON constant: {value}")
            payload = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
        except socket.timeout:
            self._send_json(408, {"error": "Request body timed out."})
            return
        except (ValueError, UnicodeDecodeError, RecursionError):
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
    print(f"ShelfScale API listening on http://{host}:{port} (models {MODEL_ID}; {NPM2018_ID}, {NPM2018_STATUS})")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="ShelfScale assessment API prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
