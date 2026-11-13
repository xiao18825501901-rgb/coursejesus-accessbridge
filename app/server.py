from __future__ import annotations

import argparse
import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.site import build_site


class AccessBridgeHandler(SimpleHTTPRequestHandler):
    """Small loopback-only static server for the generated learning app."""

    server_version = "AccessBridge/1.0"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            payload = json.dumps({"status": "ok", "app": "coursejesus-accessbridge"}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve AccessBridge on the loopback interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=15273, type=int)
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("AccessBridge local server only binds to a loopback address")
    if not args.no_build:
        build_site()
    root = Path(__file__).resolve().parents[1]
    dist = root / "app" / "dist"
    if not (dist / "index.html").exists():
        raise SystemExit("Build output is missing; run `python -m app.build` first")
    handler = partial(AccessBridgeHandler, directory=str(dist))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"AccessBridge serving http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
