import json
import threading
import urllib.error
import urllib.request

import pytest

from flowlog.viewer.server import serve


@pytest.fixture
def running_server(tmp_path):
    trace = tmp_path / "trace.jsonl"
    config = tmp_path / "flowlog.config.json"
    config.write_text(json.dumps({"lanes": [{"id": "A", "name": "A"}]}))
    server = serve(trace, config, "127.0.0.1", 0, open_browser=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}", trace
    finally:
        server.shutdown()


def test_index_serves_html(running_server):
    base, _ = running_server
    with urllib.request.urlopen(f"{base}/") as r:
        assert r.status == 200
        assert b"<html" in r.read()


def test_config_route_returns_resolved_config(running_server):
    base, _ = running_server
    with urllib.request.urlopen(f"{base}/config") as r:
        data = json.loads(r.read())
        assert data["lanes"][0]["id"] == "A"


def test_trace_jsonl_route_returns_empty_when_no_trace_yet(running_server):
    base, _ = running_server
    with urllib.request.urlopen(f"{base}/trace.jsonl") as r:
        assert r.read() == b""


def test_trace_jsonl_route_returns_written_content(running_server):
    base, trace = running_server
    trace.write_text('{"role": "A"}\n')
    with urllib.request.urlopen(f"{base}/trace.jsonl") as r:
        assert b'"role": "A"' in r.read()


def test_code_route_rejects_path_outside_root(running_server):
    base, _ = running_server
    try:
        urllib.request.urlopen(f"{base}/code?file=../../../etc/passwd&line=1")
        assert False, "expected an HTTPError"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400


def test_code_route_rejects_non_python_file(running_server, tmp_path):
    base, _ = running_server
    (tmp_path / "notes.txt").write_text("hello")
    try:
        urllib.request.urlopen(f"{base}/code?file=notes.txt&line=1")
        assert False, "expected an HTTPError"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400


def test_unknown_route_is_404(running_server):
    base, _ = running_server
    try:
        urllib.request.urlopen(f"{base}/nope")
        assert False, "expected an HTTPError"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
