"""Environment validation, run up front by `run`/`view`/`doctor` before anything
starts. Separate from `_core._trace`'s own swallow-OSError behavior, which stays
in place to protect an already-running traced app; these checks exist so a
*startup* failure is loud and specific instead of a silent no-op or a raw
traceback.
"""
import errno
import json
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

MIN_PYTHON = (3, 10)


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


def check_python_version() -> CheckResult:
    if sys.version_info[:2] >= MIN_PYTHON:
        return CheckResult("python-version", True, f"Python {sys.version.split()[0]}")
    found = sys.version.split()[0]
    return CheckResult(
        "python-version", False,
        f"flowlog requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+; found Python {found}. "
        "Upgrade your interpreter or run flowlog under a newer venv.",
    )


def check_target_script(path: str, *, as_module: bool) -> CheckResult:
    if as_module:
        return CheckResult("target", True, f"module {path}")
    if Path(path).is_file():
        return CheckResult("target", True, f"script {path}")
    return CheckResult(
        "target", False,
        f"flowlog: target script not found: {path}. Check the path, or use --module for a package/module target.",
    )


def check_trace_writable(path: str) -> CheckResult:
    import os

    parent = Path(path).resolve().parent
    pre_existed = Path(path).exists()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        os.close(fd)
        if not pre_existed:
            # O_CREAT just created an empty file purely to prove writability;
            # doctor (and run/view's pre-flight checks) must have no side effects.
            try:
                os.remove(path)
            except OSError:
                pass
        return CheckResult("trace-path", True, str(path))
    except OSError as exc:
        if exc.errno == errno.EROFS:
            return CheckResult(
                "trace-path", False,
                f"flowlog: {parent} is on a read-only filesystem. Set --trace to a writable path (e.g. /tmp).",
            )
        return CheckResult(
            "trace-path", False,
            f"flowlog: cannot write trace file at {path} ({exc.errno}: {exc.strerror}). "
            f"Choose a writable location with --trace PATH, or check permissions on {parent}.",
        )


def check_port_available(port: int, host: str = "127.0.0.1") -> CheckResult:
    if port == 0:
        return CheckResult("port", True, "auto-select")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        return CheckResult("port", True, str(port))
    except OSError:
        return CheckResult(
            "port", False,
            f"flowlog: port {port} is already in use. Pick another with --port N, "
            "or run with --port 0 to auto-select a free port.",
        )
    finally:
        sock.close()


def pick_free_port(host: str = "127.0.0.1") -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def check_config_json(path: str | None) -> CheckResult:
    if not path:
        return CheckResult("config", True, "default")
    p = Path(path)
    if not p.is_file():
        return CheckResult("config", False, f"flowlog: config file {path} not found.")
    try:
        json.loads(p.read_text())
        return CheckResult("config", True, str(path))
    except json.JSONDecodeError as exc:
        return CheckResult(
            "config", False,
            f"flowlog: config file {path} is not valid JSON ({exc}). "
            "Fix the file or omit --config to use the built-in default.",
        )


def run_checks(*checks: CheckResult) -> list[CheckResult]:
    return list(checks)


def fail_on_error(checks: list[CheckResult]) -> None:
    """Print every failing check to stderr and exit(1). Called by run/view, not doctor."""
    failed = [c for c in checks if not c.ok]
    if not failed:
        return
    for c in failed:
        print(c.message, file=sys.stderr)
    sys.exit(1)
