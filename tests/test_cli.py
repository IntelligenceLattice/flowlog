import subprocess
import sys


def run(*args, **kwargs):
    return subprocess.run([sys.executable, "-m", "flowlog", *args], capture_output=True, text=True, **kwargs)


def test_help_lists_all_subcommands():
    result = run("--help")
    assert result.returncode == 0
    for cmd in ("run", "view", "init", "doctor"):
        assert cmd in result.stdout


def test_version_flag():
    result = run("--version")
    assert result.returncode == 0
    assert "flowlog" in result.stdout


def test_doctor_runs_with_no_side_effects(tmp_path):
    trace = tmp_path / "trace.jsonl"
    result = run("doctor", "--trace", str(trace), "--port", "0")
    assert result.returncode == 0
    assert "PASS" in result.stdout
    assert not trace.exists()  # doctor only checks writability, doesn't leave a file behind


def test_run_fails_loudly_on_missing_script():
    result = run("run", "/no/such/script.py")
    assert result.returncode != 0
    assert "not found" in result.stderr


def test_init_writes_config_and_notes(tmp_path):
    (tmp_path / "app.py").write_text("def handle_request():\n    pass\n")
    result = run("init", str(tmp_path))
    assert result.returncode == 0
    assert (tmp_path / "flowlog.config.json").exists()
    assert (tmp_path / "FLOWLOG_INSTRUMENTATION_NOTES.md").exists()


def test_init_refuses_overwrite_without_force(tmp_path):
    (tmp_path / "flowlog.config.json").write_text("{}")
    result = run("init", str(tmp_path))
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_init_force_overwrites(tmp_path):
    (tmp_path / "flowlog.config.json").write_text("{}")
    result = run("init", str(tmp_path), "--force")
    assert result.returncode == 0
