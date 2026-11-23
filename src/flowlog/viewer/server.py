"""Live flow viewer: draws a traced run as it happens.

Reads the JSONL trace that flowlog's core writes when FLOWLOG_TRACE is set and
pushes each line to the browser over Server-Sent Events. The page (static/flow_viewer.html)
draws it as a sequence diagram; clicking an arrow shows the message and the code
that sent it. Standard library only.

    flowlog view --trace /path/to/trace.jsonl --config /path/to/flowlog.config.json --port 3290

  GET /             the page
  GET /config       the resolved lane/phase/kind config (see docs/config-schema.md)
  GET /events       SSE: every trace line so far, then new ones as they are written;
                    `reset` when the file is truncated (a new run started)
  GET /code         ?file=<root-relative .py>&line=N  -> lines around N (root-relative files only)
  GET /trace.jsonl  the raw trace, for offline replay (the page can load it)
"""
import argparse
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flowlog._env import check_port_available, check_trace_writable, fail_on_error, pick_free_port, run_checks

HERE = Path(__file__).resolve().parent
PAGE = HERE / "static" / "flow_viewer.html"
DEFAULT_CONFIG = HERE / "default_config.json"
DEFAULT_PORT = 3290
SNIPPET_CONTEXT = 12


def _resolve_root() -> Path:
    override = os.environ.get("FLOWLOG_ROOT")
    if override:
        return Path(override).resolve()
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return cwd


def _resolve_config(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    local = Path.cwd() / "flowlog.config.json"
    if local.is_file():
        return local
    return DEFAULT_CONFIG


class Handler(BaseHTTPRequestHandler):
    trace: Path
    root: Path
    config_path: Path

    def log_message(self, *args) -> None:  # keep the terminal quiet
        pass

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/":
            self._send(200, "text/html; charset=utf-8", PAGE.read_bytes())
        elif url.path == "/config":
            self._config()
        elif url.path == "/events":
            self._events()
        elif url.path == "/code":
            self._code(parse_qs(url.query))
        elif url.path == "/trace.jsonl":
            data = self.trace.read_bytes() if self.trace.exists() else b""
            self._send(200, "application/x-ndjson", data)
        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _config(self) -> None:
        try:
            data = self.config_path.read_bytes()
        except OSError:
            data = DEFAULT_CONFIG.read_bytes()
        self._send(200, "application/json", data)

    def _code(self, query: dict) -> None:
        try:
            rel = query["file"][0]
            line = int(query["line"][0])
            path = (self.root / rel).resolve()
            path.relative_to(self.root)          # only files inside the resolved root
            if path.suffix != ".py" or not path.is_file():
                raise ValueError
        except (KeyError, ValueError, IndexError):
            self._send(400, "text/plain", b"bad file or line")
            return
        lines = path.read_text(errors="replace").splitlines()
        start = max(1, line - SNIPPET_CONTEXT)
        end = min(len(lines), line + SNIPPET_CONTEXT)
        body = {
            "file": rel, "abs": str(path), "line": line, "start": start,
            "lines": lines[start - 1:end],
        }
        self._send(200, "application/json", json.dumps(body).encode())

    def _events(self) -> None:
        import time

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        offset, pending, idle = 0, b"", 0.0
        try:
            self._sse("hello", {"trace": str(self.trace)})
            while True:
                size = self.trace.stat().st_size if self.trace.exists() else 0
                if size < offset:                        # truncated: a new run
                    offset, pending = 0, b""
                    self._sse("reset", {})
                if size > offset:
                    with open(self.trace, "rb") as f:
                        f.seek(offset)
                        chunk = f.read(size - offset)
                    offset = size
                    pending += chunk
                    *complete, pending = pending.split(b"\n")
                    for raw in complete:
                        if raw.strip():
                            self.wfile.write(b"data: " + raw + b"\n\n")
                    self.wfile.flush()
                    idle = 0.0
                else:
                    idle += 0.2
                    if idle >= 15:                       # keep the connection alive
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        idle = 0.0
                time.sleep(0.2)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _sse(self, event: str, data: dict) -> None:
        self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
        self.wfile.flush()


def serve(trace: Path, config_path: Path, host: str, port: int, *, open_browser: bool = True) -> ThreadingHTTPServer:
    Handler.trace = trace
    Handler.root = _resolve_root()
    Handler.config_path = config_path
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    bound_port = server.server_address[1]
    url = f"http://{host}:{bound_port}"
    print(f"flowlog viewer on {url}  (trace {trace})", flush=True)
    if open_browser:
        try:
            if not webbrowser.open(url):
                print(f"flowlog: could not open a browser automatically (headless environment?). "
                      f"Viewer running at {url} - open it manually.", file=sys.stderr)
        except Exception:
            print(f"flowlog: could not open a browser automatically (headless environment?). "
                  f"Viewer running at {url} - open it manually.", file=sys.stderr)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Live viewer for a flowlog trace")
    parser.add_argument("--trace", default=os.environ.get("FLOWLOG_TRACE") or str(Path(os.environ.get("TMPDIR", "/tmp")) / "flowlog_trace.jsonl"))
    parser.add_argument("--config", default=None, help="path to flowlog.config.json (default: ./flowlog.config.json, else built-in generic default)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    config_path = _resolve_config(args.config)

    port = args.port
    checks = run_checks(check_trace_writable(str(trace_path)), check_port_available(port, args.host))
    fail_on_error(checks)
    if port == 0:
        port = pick_free_port(args.host)

    server = serve(trace_path, config_path, args.host, port, open_browser=not args.no_browser)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
