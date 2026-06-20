from __future__ import annotations

import argparse
import mimetypes
import os
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
HOTRADAR_DIST = ROOT / "frontend" / "dist"
JPNOTE_ROOT = Path(
    os.environ.get(
        "HOTRADAR_JP_NOTEBOOK_ROOT",
        "/Users/lanyangyang/Documents/Japanese_notebook_codex",
    )
)

HOTRADAR_DOMAIN = os.environ.get("HOTRADAR_LOCAL_DOMAIN", "hotradar.test").lower()
JPNOTE_DOMAIN = os.environ.get("JPNOTE_LOCAL_DOMAIN", "jpnote.test").lower()
BACKEND_URL = os.environ.get("HOTRADAR_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
JPNOTE_STORAGE_KEY = "japanese-vocab-notebook.words"

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def host_name(raw_host: str | None) -> str:
    if not raw_host:
        return ""
    return raw_host.split(":", 1)[0].lower()


def safe_static_path(root: Path, request_path: str) -> Path | None:
    path = unquote(urlsplit(request_path).path)
    path = path.lstrip("/")
    candidate = (root / path).resolve()
    root_resolved = root.resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None

    if candidate.is_dir():
        return candidate / "index.html"
    return candidate


class LocalDomainHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self.route_request()

    def do_HEAD(self) -> None:
        self.route_request(send_body=False)

    def do_POST(self) -> None:
        self.route_request()

    def do_PUT(self) -> None:
        self.route_request()

    def do_PATCH(self) -> None:
        self.route_request()

    def do_DELETE(self) -> None:
        self.route_request()

    def route_request(self, send_body: bool = True) -> None:
        host = host_name(self.headers.get("Host"))

        if host == HOTRADAR_DOMAIN:
            if urlsplit(self.path).path.startswith("/api/"):
                self.proxy_to_backend(send_body=send_body)
                return
            self.serve_static(HOTRADAR_DIST, spa_fallback=True, send_body=send_body)
            return

        if host == JPNOTE_DOMAIN:
            if urlsplit(self.path).path == "/__jpnote_receive":
                self.receive_jpnote_migration(send_body=send_body)
                return
            self.serve_static(JPNOTE_ROOT, spa_fallback=True, send_body=send_body)
            return

        message = (
            f"Unknown local domain. Use http://{HOTRADAR_DOMAIN} "
            f"or http://{JPNOTE_DOMAIN}."
        )
        self.send_text(HTTPStatus.NOT_FOUND, message, send_body=send_body)

    def proxy_to_backend(self, send_body: bool = True) -> None:
        target_url = f"{BACKEND_URL}{self.path}"
        content_length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(content_length) if content_length else None

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "host"
        }

        request = Request(target_url, data=body, headers=headers, method=self.command)

        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read()
                self.send_response(response.status)
                self.copy_response_headers(response.headers.items(), len(response_body))
                self.end_headers()
                if send_body:
                    self.wfile.write(response_body)
        except HTTPError as exc:
            response_body = exc.read()
            self.send_response(exc.code)
            self.copy_response_headers(exc.headers.items(), len(response_body))
            self.end_headers()
            if send_body:
                self.wfile.write(response_body)
        except URLError as exc:
            self.send_text(
                HTTPStatus.BAD_GATEWAY,
                f"HotRadar backend is not reachable at {BACKEND_URL}: {exc.reason}",
                send_body=send_body,
            )

    def copy_response_headers(self, headers: list[tuple[str, str]], body_length: int) -> None:
        for key, value in headers:
            if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "content-length":
                self.send_header(key, value)
        self.send_header("Content-Length", str(body_length))

    def receive_jpnote_migration(self, send_body: bool = True) -> None:
        if self.command != "POST":
            self.send_text(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "Open the migration page from http://127.0.0.1:5173/jpnote-migrate.html first.",
                send_body=send_body,
            )
            return

        content_length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(content_length).decode("utf-8") if content_length else ""
        payload = parse_qs(body).get("payload", [""])[0]

        if not payload:
            self.send_text(HTTPStatus.BAD_REQUEST, "Migration payload is empty.", send_body=send_body)
            return

        html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Japanese Notebook Migration Complete</title>
    <style>
      body {{
        display: grid;
        min-height: 100vh;
        margin: 0;
        place-items: center;
        color: #202624;
        background: #f6f8f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans", "Microsoft YaHei", sans-serif;
      }}
      main {{
        width: min(560px, calc(100vw - 32px));
        border: 1px solid #d9e2dd;
        border-radius: 8px;
        padding: 24px;
        background: #fff;
        box-shadow: 0 12px 28px rgba(27, 42, 37, 0.08);
      }}
      a {{
        display: inline-flex;
        min-height: 40px;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        padding: 0 14px;
        color: #fff;
        background: #24776b;
        text-decoration: none;
      }}
      p {{ color: #65736e; line-height: 1.6; }}
    </style>
  </head>
  <body>
    <main>
      <h1>迁移完成</h1>
      <p id="status">正在写入新地址的本地数据...</p>
      <a href="/">打开日语笔记本</a>
    </main>
    <script>
      const payload = {json.dumps(payload)};
      localStorage.setItem({json.dumps(JPNOTE_STORAGE_KEY)}, payload);
      let count = 0;
      try {{
        const parsed = JSON.parse(payload);
        count = Array.isArray(parsed) ? parsed.length : 0;
      }} catch {{}}
      document.querySelector("#status").textContent = `已写入 ${{count}} 个单词到 jpnote.test:8088。`;
    </script>
  </body>
</html>
"""
        content = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if send_body:
            self.wfile.write(content)

    def serve_static(self, root: Path, spa_fallback: bool, send_body: bool = True) -> None:
        if not root.exists():
            self.send_text(
                HTTPStatus.SERVICE_UNAVAILABLE,
                f"Static root does not exist: {root}",
                send_body=send_body,
            )
            return

        target = safe_static_path(root, self.path)
        if target is None:
            self.send_text(HTTPStatus.FORBIDDEN, "Forbidden", send_body=send_body)
            return

        if not target.exists() and spa_fallback:
            target = root / "index.html"

        if not target.exists() or not target.is_file():
            self.send_text(HTTPStatus.NOT_FOUND, "Not found", send_body=send_body)
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if send_body:
            self.wfile.write(content)

    def send_text(self, status: HTTPStatus, text: str, send_body: bool = True) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} {self.headers.get('Host', '-')} {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve HotRadar and Japanese Notebook by local domain.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LOCAL_DOMAIN_PORT", "8088")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), LocalDomainHandler)
    print(f"Local domain gateway listening on http://{args.host}:{args.port}")
    print(f"HotRadar: http://{HOTRADAR_DOMAIN}:{args.port}")
    print(f"Japanese Notebook: http://{JPNOTE_DOMAIN}:{args.port}")
    print(f"HotRadar API proxy: {BACKEND_URL}")
    print(f"Japanese Notebook root: {JPNOTE_ROOT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local domain gateway.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
