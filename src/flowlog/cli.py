"""`flowlog` console script: run / view / init / doctor."""
import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from flowlog._env import (
    check_config_json,
    check_port_available,
    check_python_version,
    check_target_script,
    check_trace_writable,
    fail_on_error,
    pick_free_port,
    run_checks,
)
from flowlog.scaffold.init import run_init
from flowlog.viewer.server import DEFAULT_PORT, _resolve_config, serve


def _default_trace_path() -> Path:
    tmp = Path(tempfile.gettempdir())
    return tmp / f"flowlog-{int(time.time())}-{os.getpid()}.jsonl"


def cmd_run(args: argparse.Namespace) -> int:
    checks = run_checks(check_python_version())
    fail_on_error(checks)
    checks = run_checks(check_target_script(args.target, as_module=args.module))
    fail_on_error(checks)

    trace_path = Path(args.trace) if args.trace else _default_trace_path()
    config_path = _resolve_config(args.config)
    port = args.port
    fail_on_error(run_checks(check_trace_writable(str(trace_path)), check_port_available(port)))
    if port == 0:
        port = pick_free_port()

    env = dict(os.environ)
    env["FLOWLOG_TRACE"] = str(trace_path)

    server = serve(trace_path, config_path, "127.0.0.1", port, open_browser=not args.no_browser)
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    script_args = args.script_args[1:] if args.script_args[:1] == ["--"] else args.script_args
    cmd = [sys.executable, "-m", args.target] if args.module else [sys.executable, str(args.target)]
    cmd += script_args
    try:
        proc = subprocess.run(cmd, env=env)
        if not args.exit:
            # keep the viewer up after the script finishes, so the trace can be inspected
            print(f"flowlog: script exited ({proc.returncode}); viewer still running at "
                  f"http://127.0.0.1:{port} - press Ctrl+C to stop.", flush=True)
            try:
                thread.join()
            except KeyboardInterrupt:
                pass
        return proc.returncode
    finally:
        server.shutdown()


def cmd_view(args: argparse.Namespace) -> int:
    trace_path = Path(args.trace) if args.trace else Path(os.environ.get("FLOWLOG_TRACE") or _default_trace_path())
    config_path = _resolve_config(args.config)
    port = args.port
    fail_on_error(run_checks(check_trace_writable(str(trace_path)), check_port_available(port), check_config_json(args.config)))
    if port == 0:
        port = pick_free_port()
    server = serve(trace_path, config_path, "127.0.0.1", port, open_browser=not args.no_browser)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    return run_init(Path(args.target_dir), force=args.force)


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_checks(
        check_python_version(),
        check_trace_writable(args.trace or str(_default_trace_path())),
        check_port_available(args.port),
    )
    ok = True
    for c in checks:
        status = "PASS" if c.ok else "FAIL"
        print(f"[{status}] {c.name}: {c.message}")
        ok = ok and c.ok
    return 0  # doctor always exits 0; failures are reported, not raised


def build_parser() -> argparse.ArgumentParser:
    from flowlog import __version__

    parser = argparse.ArgumentParser(prog="flowlog", description="Trace how your processes, agents, and MCP servers talk, and watch it as a live sequence diagram")
    parser.add_argument("--version", action="version", version=f"flowlog {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser(
        "run", help="run a script/module with tracing enabled and open the viewer",
        description="flowlog flags must come before TARGET. Everything after TARGET "
                     "(including a bare --) is passed through to it unchanged.",
    )
    p_run.add_argument("--trace")
    p_run.add_argument("--config")
    p_run.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_run.add_argument("--no-browser", action="store_true")
    p_run.add_argument("--module", action="store_true")
    p_run.add_argument("--exit", action="store_true", help="stop the viewer as soon as the script exits")
    p_run.add_argument("target")
    p_run.add_argument("script_args", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)

    p_view = sub.add_parser("view", help="standalone viewer against an existing/growing trace")
    p_view.add_argument("--trace")
    p_view.add_argument("--config")
    p_view.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_view.add_argument("--no-browser", action="store_true")
    p_view.set_defaults(func=cmd_view)

    p_init = sub.add_parser("init", help="scaffold flowlog.config.json + instrumentation notes for a target project")
    p_init.add_argument("target_dir", nargs="?", default=".")
    p_init.add_argument("--lang", default="python")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_doctor = sub.add_parser("doctor", help="validate the environment with no side effects")
    p_doctor.add_argument("--trace")
    p_doctor.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
