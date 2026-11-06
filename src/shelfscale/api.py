"""ShelfScale assessment API (prototype, standard library only).

Endpoints:
    GET  /                -> the ShelfScale page (HTML; static files under /static/)
    GET  /api             -> public service summary (JSON; formerly at /)
    GET  /health          -> {"status": "ok", "models": {"uk-npm-2004/05": "in force",
                                                  "uk-npm-2018": "shadow model, not in force"}}
    POST /v1/assess       -> one product  (see service.assess_product)
    POST /v1/assess/bulk  -> many products (see service.assess_bulk)
    POST /v1/lookup       -> one CoFID food by code or exact name (see cofid_assess)
    POST /v1/lookup/bulk  -> many lookups (see cofid_assess.lookup_bulk)

Run locally:
    PYTHONPATH=src python3 -m shelfscale.api --port 8765

Browser routes (same origin, used by the page; no key in the browser):
    GET  /ui/search?q=    -> food names and codes (ui_api.search)
    GET  /ui/food/<id>    -> one CoFID food with portions and provenance (ui_api.food)
    POST /ui/recipe       -> a recipe, scored and labelled (recipe.calculate)
These call the same in-process functions as the keyed API and share their
own rolling quota (UI_RATE_LIMIT), separate from the API key's quota.

Set SHELFSCALE_API_KEY before startup. All four POST routes require X-API-Key
and share a 60-request rolling-minute quota per process. Public GET routes are
unmetered. Asynchronous bulk jobs are specified but not implemented.
"""

from __future__ import annotations

import argparse
from collections import deque
import hmac
import json
import math
import os
import re
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .cofid_assess import lookup_and_assess, lookup_bulk
from .npm2018 import MODEL_ID as NPM2018_ID
from . import laws
from .service import MODEL_ID, MAX_BULK_ITEMS, assess_bulk, assess_product
from .lookup import DATA_RELEASE, _index
from . import bulk, matching, recipe, ui_api

ROUTES = {
    "/v1/assess": assess_product,
    "/v1/assess/bulk": assess_bulk,
    "/v1/lookup": lookup_and_assess,
    "/v1/lookup/bulk": lookup_bulk,
}

MAX_BODY_BYTES = 5_000_000
RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60
UI_RATE_LIMIT = 300
UI_MAX_BODY_BYTES = 256_000
PAGE_POSTS = {
    "/ui/recipe": recipe.calculate,
    "/ui/bulk": bulk.run,
    "/ui/match": lambda payload: matching.propose(payload.get("name") if isinstance(payload, dict) else None),
    "/ui/match/confirm": lambda payload: record_confirmation(payload),
}
CONFIRMATIONS_VAR = "SHELFSCALE_CONFIRMATIONS_PATH"


def record_confirmation(payload):
    """Validate a confirmed match. Kept in the visitor's browser; appended to a file only when
    SHELFSCALE_CONFIRMATIONS_PATH names durable storage."""
    record = matching.confirmation(payload)
    record["confirmed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = os.environ.get(CONFIRMATIONS_VAR)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        record["stored"] = "service file"
    else:
        record["stored"] = ("your browser only: this service has no durable storage configured. "
                            "Export your confirmations to add them to the reviewed mapping.")
    return record
WEB = Path(__file__).resolve().parent / "web"
STATIC = {  # fixed list: nothing else on disk is ever served
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/icon.svg": ("icon.svg", "image/svg+xml"),
}
PAGE_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data:; style-src 'self'; "
                                "script-src 'self'; connect-src 'self'; base-uri 'none'; "
                                "form-action 'none'; frame-ancestors 'none'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class RateLimiter:
    """One bounded rolling window for the server's single key, under a lock."""

    def __init__(self, clock=time.monotonic, limit=RATE_LIMIT):
        self.clock = clock
        self.limit = limit
        self.requests = deque()
        self.lock = threading.Lock()

    def admit(self) -> int:
        """Return zero when admitted, otherwise Retry-After seconds."""
        with self.lock:
            now = self.clock()
            while self.requests and self.requests[0] <= now - RATE_WINDOW_SECONDS:
                self.requests.popleft()
            if len(self.requests) >= self.limit:
                return max(1, math.ceil(self.requests[0] + RATE_WINDOW_SECONDS - now))
            self.requests.append(now)
            return 0


class ShelfScaleServer(ThreadingHTTPServer):
    def __init__(self, address, *, api_key=None, limiter=None, ui_limiter=None):
        key = os.environ.get("SHELFSCALE_API_KEY") if api_key is None else api_key
        if not isinstance(key, str) or not key or any(not 33 <= ord(c) <= 126 for c in key):
            raise ValueError("SHELFSCALE_API_KEY must be set to a nonempty printable ASCII token without spaces.")
        self.api_key = key.encode("ascii")
        self.limiter = limiter if limiter is not None else RateLimiter()
        self.ui_limiter = ui_limiter if ui_limiter is not None else RateLimiter(limit=UI_RATE_LIMIT)
        revision = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "")
        self.revision = revision if re.fullmatch(r"[0-9a-fA-F]{40}", revision) else None
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "ShelfScale/0.1"

    def _send_json(self, status: int, body: dict, *, retry_after: int | None = None) -> None:
        raw = json.dumps(body, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if retry_after is not None:
            self.send_header("Retry-After", str(retry_after))
        self.end_headers()
        self.wfile.write(raw)

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def _send_file(self, name: str, content_type: str) -> None:
        raw = (WEB / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        for header, value in PAGE_HEADERS.items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(raw)

    def _ui_admitted(self) -> bool:
        retry_after = self.server.ui_limiter.admit()
        if retry_after:
            self._send_json(429, {"error": "The page is busy. Try again shortly."}, retry_after=retry_after)
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        parts = urlsplit(self.path)
        path = parts.path
        models = laws.summary()
        if path in STATIC and (path != "/" or not parts.query):
            self._send_file(*STATIC[path])
        elif path == "/health":
            self._send_json(200, {"status": "ok", "models": models,
                                  "revision": self.server.revision})
        elif path == "/api":
            self._send_json(200, {
                "service": "ShelfScale Open", "models": models,
                "data_release": DATA_RELEASE, "revision": self.server.revision,
                "laws": [laws.label(m) for m in laws.models()],
                "endpoints": {"public": ["GET / (page)", "GET /api", "GET /health"],
                              "authenticated": [f"POST {path}" for path in ROUTES],
                              "page": ["GET /ui/search", "GET /ui/food/<food_id>", *(f"POST {p}" for p in PAGE_POSTS)]},
                "authentication": {"header": "X-API-Key", "required_for_post": True},
                "limits": {"requests": RATE_LIMIT, "window_seconds": RATE_WINDOW_SECONDS,
                           "scope": "one shared key per process; resets on restart",
                           "bulk_items": MAX_BULK_ITEMS, "body_bytes": MAX_BODY_BYTES,
                           "page_requests": UI_RATE_LIMIT},
                "docs": "https://github.com/elliotkarikari/Product-nutrition-database/blob/shelfscale-open/docs/API.md",
            })
        elif path == "/ui/search" or path.startswith("/ui/food/"):
            if not self._ui_admitted():
                return
            params = {k: v[-1] for k, v in parse_qs(parts.query, max_num_fields=8).items()}
            try:
                if path == "/ui/search":
                    self._send_json(200, ui_api.search(params.get("q", "")))
                else:
                    self._send_json(200, ui_api.food(unquote(path[len("/ui/food/"):]), params))
            except LookupError as exc:
                self._send_json(404, {"error": str(exc)})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        page = self.path in PAGE_POSTS
        if self.path not in ROUTES and not page:
            self._send_json(404, {"error": "Not found."})
            return
        if page:
            if not self._ui_admitted():
                return
            handler = PAGE_POSTS[self.path]
        else:
            keys = self.headers.get_all("X-API-Key", [])
            if len(keys) != 1 or not hmac.compare_digest(keys[0].encode("utf-8"), self.server.api_key):
                self._send_json(401, {"error": "Valid X-API-Key required."})
                return
            retry_after = self.server.limiter.admit()
            if retry_after:
                self._send_json(429, {"error": "Rate limit exceeded."}, retry_after=retry_after)
                return
            handler = ROUTES[self.path]
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._send_json(400, {"error": "Supply one numeric Content-Length; transfer encoding is unsupported."})
            return
        try:
            length = int(lengths[0])
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length."})
            return
        if length <= 0 or length > (UI_MAX_BODY_BYTES if page else MAX_BODY_BYTES):
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
            self._send_json(200, handler(payload))
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:  # keep test output clean
        pass


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    with ShelfScaleServer((host, port)) as server:
        # Verify snapshots and compose the index before advertising readiness.
        laws.models()               # refuse to start on a bad law configuration
        matching.settings()
        _index()
        ui_api.foods_by_id()
        ui_api.search("warm")       # builds the portion and overlay tables before readiness
        print(f"ShelfScale API listening on http://{host}:{port} (laws: {laws.summary()})", flush=True)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="ShelfScale assessment API prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        run(args.host, args.port)
    except ValueError as exc:
        parser.exit(1, f"ShelfScale startup failed: {exc}\n")


if __name__ == "__main__":
    main()
