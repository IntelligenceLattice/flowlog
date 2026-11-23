import json
import os

import pytest

import flowlog
from flowlog import _core


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("FLOWLOG_TRACE", raising=False)
    monkeypatch.delenv("FLOWLOG_ROOT", raising=False)
    yield


def test_send_recv_note_print_arrowed_lines(capsys):
    flowlog.send("HOST", "SERVER", "hello", kind="greet")
    flowlog.recv("HOST", "SERVER", "hi back", kind="greet_reply")
    flowlog.note("HOST", "just a note")
    out = capsys.readouterr().out
    assert "[HOST  ] --> SERVER  hello" in out
    assert "[HOST  ] <-- SERVER  hi back" in out
    assert "[HOST  ]     just a note" in out


def test_event_never_prints(capsys):
    flowlog.event("SERVER", "send", "BACKEND", "search", kind="backend_search")
    out = capsys.readouterr().out
    assert out == ""


def test_quiet_suppresses_output(capsys):
    flowlog.quiet(True)
    try:
        flowlog.send("HOST", "SERVER", "silent")
        assert capsys.readouterr().out == ""
    finally:
        flowlog.quiet(False)


def test_capture_collects_lines_and_still_prints(capsys):
    with flowlog.capture() as lines:
        flowlog.send("HOST", "SERVER", "captured")
    assert any("captured" in line for line in lines)
    assert "captured" in capsys.readouterr().out


def test_trace_is_noop_without_env_var(tmp_path, capsys):
    trace = tmp_path / "trace.jsonl"
    flowlog.send("HOST", "SERVER", "no trace expected")
    capsys.readouterr()
    assert not trace.exists()


def test_trace_writes_jsonl_when_env_var_set(tmp_path, monkeypatch, capsys):
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("FLOWLOG_TRACE", str(trace))
    flowlog.send("HOST", "SERVER", "traced", kind="greet", payload={"a": 1})
    capsys.readouterr()
    lines = trace.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["role"] == "HOST"
    assert record["dir"] == "send"
    assert record["peer"] == "SERVER"
    assert record["kind"] == "greet"
    assert record["payload"] == {"a": 1}
    assert record["code"]["func"] == "test_trace_writes_jsonl_when_env_var_set"


def test_trace_empty_string_is_also_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FLOWLOG_TRACE", "")
    flowlog.send("HOST", "SERVER", "still no trace")
    capsys.readouterr()
    # nothing to assert on disk since no path was given; absence of a crash is the point


def test_trace_survives_unwritable_path(monkeypatch, capsys):
    monkeypatch.setenv("FLOWLOG_TRACE", "/nonexistent-dir-xyz/trace.jsonl")
    flowlog.send("HOST", "SERVER", "must not raise")
    capsys.readouterr()  # no exception means the OSError was swallowed, as documented


def test_payload_truncated_past_limit(tmp_path, monkeypatch, capsys):
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("FLOWLOG_TRACE", str(trace))
    big = "x" * (_core._PAYLOAD_LIMIT + 1000)
    flowlog.send("HOST", "SERVER", "big payload", payload=big)
    capsys.readouterr()
    record = json.loads(trace.read_text().splitlines()[0])
    assert record["payload"]["truncated"] is True


def test_short_truncates_long_text():
    assert flowlog.short("a" * 200, limit=10).endswith("...")
    assert len(flowlog.short("a" * 200, limit=10)) == 10


def test_short_renders_non_string_as_json():
    assert flowlog.short({"a": 1}) == '{"a": 1}'


def test_repo_root_override(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWLOG_ROOT", str(tmp_path))
    nested = tmp_path / "pkg" / "mod.py"
    nested.parent.mkdir()
    nested.write_text("x = 1")
    root = _core._repo_root(nested)
    assert root == tmp_path.resolve()


def test_rule_writes_trace_record(tmp_path, monkeypatch, capsys):
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("FLOWLOG_TRACE", str(trace))
    flowlog.rule("a scenario")
    capsys.readouterr()
    record = json.loads(trace.read_text().splitlines()[0])
    assert record["kind"] == "rule"
    assert record["text"] == "a scenario"
