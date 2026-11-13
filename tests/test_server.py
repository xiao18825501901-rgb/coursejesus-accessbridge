from __future__ import annotations

import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from app.server import AccessBridgeHandler
from app.site import build_site


def test_loopback_health_and_index(tmp_path) -> None:
    build_site(tmp_path)
    handler = partial(AccessBridgeHandler, directory=str(tmp_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3) as response:
            assert json.loads(response.read())["status"] == "ok"
            assert response.headers["X-Content-Type-Options"] == "nosniff"
        with urlopen(f"http://127.0.0.1:{port}/index.html", timeout=3) as response:
            assert response.status == 200
            assert b"CourseJesus" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
