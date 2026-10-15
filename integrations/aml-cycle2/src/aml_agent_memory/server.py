"""HTTP service exposing Agent Memory through the AML Cycle 2 Add/Search contract.

Routes: ``GET /health`` (unauthenticated), ``POST /add`` and ``POST /search`` (authenticated
with ``Authorization: Bearer <key>``, ``Authorization: Token <key>`` or ``X-Api-Key: <key>``).
Standard library only; run behind a TLS-terminating reverse proxy.
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import signal
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .contract import ContractError, add_payload_digest, add_response, error_body, validate_add, validate_search
from .store import IdempotencyConflict, MemoryStore, WriteRefused, user_key

LOG = logging.getLogger("aml_agent_memory")
MAX_BODY_BYTES = 16 * 1024 * 1024
MIN_KEY_LENGTH = 16


class AMLServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store: MemoryStore, api_key: str, max_inflight: int = 128) -> None:
        if len(api_key) < MIN_KEY_LENGTH:
            raise ValueError(f"memory system key must be at least {MIN_KEY_LENGTH} characters")
        super().__init__(address, Handler)
        self.store = store
        self.api_key = api_key.encode("utf-8")
        self.inflight = threading.BoundedSemaphore(max_inflight)


class Handler(BaseHTTPRequestHandler):
    server: AMLServer
    protocol_version = "HTTP/1.1"
    server_version = f"agent-memory-aml/{__version__}"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - BaseHTTPRequestHandler API
        return  # request bodies and client addresses are not logged; see _respond

    def _respond(self, status: int, payload: dict, started: float, user: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        LOG.info(
            "%s %s %d %.1fms%s", self.command, self.path, status, (time.perf_counter() - started) * 1000,
            f" user={user[:12]}" if user else "",
        )

    def _authorized(self) -> bool:
        presented: list[str] = []
        authorization = self.headers.get("Authorization", "")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() in ("bearer", "token") and credential.strip():
            presented.append(credential.strip())
        if self.headers.get("X-Api-Key"):
            presented.append(self.headers["X-Api-Key"].strip())
        return any(hmac.compare_digest(value.encode("utf-8"), self.server.api_key) for value in presented)

    def _read_json(self, started: float):
        length = self.headers.get("Content-Length")
        if length is None or not length.isdigit():
            self._respond(HTTPStatus.LENGTH_REQUIRED, error_body("content_length_required"), started)
            return None
        if int(length) > MAX_BODY_BYTES:
            self._respond(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error_body("body_too_large"), started)
            return None
        raw = self.rfile.read(int(length))
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._respond(HTTPStatus.BAD_REQUEST, error_body("invalid_json"), started)
            return None

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        started = time.perf_counter()
        if self.path.split("?", 1)[0] == "/health":
            self._respond(HTTPStatus.OK, {"status": "ok"}, started)
        else:
            self._respond(HTTPStatus.NOT_FOUND, error_body("not_found"), started)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        started = time.perf_counter()
        route = self.path.split("?", 1)[0]
        if route not in ("/add", "/search"):
            self._respond(HTTPStatus.NOT_FOUND, error_body("not_found"), started)
            return
        if not self._authorized():
            self._respond(HTTPStatus.UNAUTHORIZED, error_body("unauthorized"), started)
            return
        if not self.server.inflight.acquire(blocking=False):
            self._respond(HTTPStatus.TOO_MANY_REQUESTS, error_body("too_many_inflight_requests"), started)
            return
        try:
            body = self._read_json(started)
            if body is None:
                return
            if route == "/add":
                self._add(body, started)
            else:
                self._search(body, started)
        finally:
            self.server.inflight.release()

    def _add(self, body, started: float) -> None:
        try:
            add = validate_add(body)
        except ContractError as exc:
            self._respond(HTTPStatus.UNPROCESSABLE_ENTITY, error_body("invalid_request", exc.errors), started)
            return
        user = user_key(add["user_id"])
        try:
            self.server.store.add(add, add_payload_digest(add))
        except IdempotencyConflict:
            self._respond(HTTPStatus.CONFLICT, error_body("request_id_reused_with_different_payload"), started, user)
            return
        except WriteRefused as exc:
            LOG.error("write refused user=%s: %s", user[:12], exc)
            self._respond(HTTPStatus.INTERNAL_SERVER_ERROR, error_body("memory_write_refused"), started, user)
            return
        except Exception:  # noqa: BLE001 - every unexpected failure is a retryable 500, never a false 200
            LOG.exception("add failed user=%s", user[:12])
            self._respond(HTTPStatus.INTERNAL_SERVER_ERROR, error_body("internal_error"), started, user)
            return
        self._respond(HTTPStatus.OK, add_response(add), started, user)

    def _search(self, body, started: float) -> None:
        try:
            search = validate_search(body)
        except ContractError as exc:
            self._respond(HTTPStatus.UNPROCESSABLE_ENTITY, error_body("invalid_request", exc.errors), started)
            return
        user = user_key(search["user_id"])
        query = search["query"]
        if search["options"]:
            # Multiple-choice options widen the lexical query; the question text is kept verbatim.
            query = "\n".join([query, *search["options"]])
        try:
            items = self.server.store.search(search["user_id"], query, search["top_k"])
        except Exception:  # noqa: BLE001
            LOG.exception("search failed user=%s", user[:12])
            self._respond(HTTPStatus.INTERNAL_SERVER_ERROR, error_body("internal_error"), started, user)
            return
        self._respond(HTTPStatus.OK, {"data": items}, started, user)


def _load_key(args: argparse.Namespace) -> str:
    if args.key_file:
        return Path(args.key_file).read_text(encoding="utf-8").strip()
    return os.environ.get("AML_MEMORY_KEY", "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--key-file", help="file holding the memory system key (default: $AML_MEMORY_KEY)")
    parser.add_argument("--max-open-users", type=int, default=64)
    parser.add_argument("--max-inflight", type=int, default=128)
    parser.add_argument("--compute-slots", type=int, default=1, help="runtime operations allowed to run at once")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)

    key = _load_key(args)
    if len(key) < MIN_KEY_LENGTH:
        parser.error(f"a memory system key of at least {MIN_KEY_LENGTH} characters is required (AML_MEMORY_KEY or --key-file)")
    store = MemoryStore(args.data_dir, max_open=args.max_open_users, compute_slots=args.compute_slots)
    server = AMLServer((args.host, args.port), store, key, max_inflight=args.max_inflight)

    def stop(*_: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    LOG.info("agent-memory AML service %s listening on %s:%d data=%s", __version__, args.host, server.server_port, args.data_dir)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
