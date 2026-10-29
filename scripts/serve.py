"""A small web server for the browser build, for this machine only.

    python -I scripts/serve.py [port]        # default port 8080

Serves build/web/ at http://localhost:<port>. It listens on 127.0.0.1 only,
so nothing outside this computer can reach the converted game files
(CLAUDE.md rule 1). Python's own server cannot answer "Range" requests (a
request for part of a file, which a browser's sound player makes), so this
one does, and it sends WebAssembly with its proper type.

For the checks, /_served.json counts what was sent since the server
started: per path, whole files (200) and parts (206).
"""

import json
import threading

import mimetypes
import re
import sys
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = (Path(__file__).resolve().parent.parent / "build" / "web").resolve()
TYPES = {".wasm": "application/wasm", ".js": "text/javascript",
         ".json": "application/json", ".html": "text/html; charset=utf-8",
         ".ogg": "audio/ogg"}
FINGERPRINTED = re.compile(r"\.[0-9a-f]{12}\.[a-z0-9]+$")
SERVED = {}                     # path -> {"200": n, "206": n}
SERVED_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "pp-serve"

    def do_HEAD(self):
        self.send_file(head_only=True)

    def do_GET(self):
        self.send_file(head_only=False)

    def find(self):
        path = unquote(urlsplit(self.path).path)
        if path.endswith("/"):
            path += "index.html"
        target = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in target.parents or not target.is_file():
            return None
        return target

    def send_file(self, head_only):
        if urlsplit(self.path).path == "/_served.json":
            with SERVED_LOCK:
                body = json.dumps(SERVED).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        target = self.find()
        if target is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = target.stat().st_size
        start, end, status = 0, size - 1, HTTPStatus.OK
        rng = self.headers.get("Range")
        if rng:
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
            if not m or (m.group(1) == "" and m.group(2) == ""):
                status = None
            elif m.group(1) == "":                 # the last N bytes
                start, end = max(0, size - int(m.group(2))), size - 1
                status = HTTPStatus.PARTIAL_CONTENT
            else:
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
                status = HTTPStatus.PARTIAL_CONTENT
            if status is None or start > end or start >= size:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
        ctype = TYPES.get(target.suffix) or mimetypes.guess_type(target.name)[0] \
            or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        # A fingerprinted name never changes its bytes; everything else is
        # checked every time.
        if FINGERPRINTED.search(target.name):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.send_header("Last-Modified", formatdate(target.stat().st_mtime, usegmt=True))
        self.end_headers()
        if head_only:
            return
        with SERVED_LOCK:
            counts = SERVED.setdefault(unquote(urlsplit(self.path).path), {})
            counts[str(int(status))] = counts.get(str(int(status)), 0) + 1
        with target.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    return
                left -= len(chunk)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    if not ROOT.is_dir():
        sys.exit(f"{ROOT} does not exist: run scripts/build_web.py first")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving {ROOT}\nOpen http://localhost:{port}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
