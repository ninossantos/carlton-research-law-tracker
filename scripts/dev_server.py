#!/usr/bin/env python3
"""Local dashboard server on 127.0.0.1:8765. Serves public/ and proxies /api/bills."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
ENV_PATH = ROOT / ".env"
HOST = "127.0.0.1"
PORT = 8765


def load_env(path: Path) -> dict:
    env = {}
    if not path.is_file():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env(ENV_PATH)
# Merge into os.environ without printing values.
for k, v in ENV.items():
    os.environ.setdefault(k, v)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", "frame-ancestors *")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "OPENSTATES" in msg.upper() or "api_key" in msg.lower():
            return
        super().log_message("%s", msg)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/bills":
            self.proxy_bills(parsed)
            return
        super().do_GET()

    def proxy_bills(self, parsed):
        key = os.environ.get("OPENSTATES_API_KEY", "")
        if not key:
            self._json({"error": "Open States proxy is not configured."}, 500)
            return
        qs = urllib.parse.parse_qs(parsed.query)
        page = (qs.get("page") or ["1"])[0]
        params = {
            "q": '"coercive control"',
            "sort": "updated_desc",
            "per_page": "20",
            "page": page,
        }
        url = "https://v3.openstates.org/bills?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"X-API-KEY": key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                status = resp.status
        except urllib.error.HTTPError as err:
            body = err.read()
            status = err.code
        except urllib.error.URLError:
            self._json({"error": "Open States results did not load."}, 502)
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, status):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving {PUBLIC} at http://{HOST}:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
