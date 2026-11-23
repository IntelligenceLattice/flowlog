import json
import socket
import sys

from flowlog._env import (
    check_config_json,
    check_port_available,
    check_python_version,
    check_target_script,
    check_trace_writable,
)


def test_python_version_passes_on_current_interpreter():
    assert check_python_version().ok is True


def test_python_version_fails_when_mocked_old(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 9, 0))
    result = check_python_version()
    assert result.ok is False
    assert "3.10" in result.message


def test_target_script_missing():
    result = check_target_script("/no/such/script.py", as_module=False)
    assert result.ok is False
    assert "not found" in result.message


def test_target_script_found(tmp_path):
    script = tmp_path / "x.py"
    script.write_text("pass")
    assert check_target_script(str(script), as_module=False).ok is True


def test_target_module_skips_filesystem_check():
    assert check_target_script("some.module", as_module=True).ok is True


def test_trace_writable_succeeds(tmp_path):
    result = check_trace_writable(str(tmp_path / "trace.jsonl"))
    assert result.ok is True


def test_trace_unwritable_directory_fails():
    result = check_trace_writable("/nonexistent-dir-xyz/trace.jsonl")
    assert result.ok is False
    assert "cannot write trace file" in result.message


def test_port_available_on_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    assert check_port_available(port).ok is True


def test_port_unavailable_when_bound():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    try:
        result = check_port_available(port)
        assert result.ok is False
        assert "already in use" in result.message
    finally:
        sock.close()


def test_port_zero_means_auto_select():
    assert check_port_available(0).ok is True


def test_config_json_default_when_none():
    assert check_config_json(None).ok is True


def test_config_json_valid(tmp_path):
    path = tmp_path / "flowlog.config.json"
    path.write_text(json.dumps({"lanes": []}))
    assert check_config_json(str(path)).ok is True


def test_config_json_invalid(tmp_path):
    path = tmp_path / "flowlog.config.json"
    path.write_text("{not valid json")
    result = check_config_json(str(path))
    assert result.ok is False
    assert "not valid JSON" in result.message


def test_config_json_missing_file(tmp_path):
    result = check_config_json(str(tmp_path / "missing.json"))
    assert result.ok is False
