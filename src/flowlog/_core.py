"""One printer for a whole flow, so every traced process logs through it.

Every line is  [ROLE  ] --> TARGET  what was sent
          or   [ROLE  ] <-- SOURCE  what came back
          or   [ROLE  ]     note

Roles, kinds and peers are free-form strings you choose - flowlog has no
built-in vocabulary. Pick names that match your own components.

With FLOWLOG_TRACE=<path> set, every line is also appended to that file as one
JSON object: role, direction, peer, text, plus an optional `kind` (which step
this is), the full `payload`, and the code location that logged it. The
flowlog viewer reads that file and draws the run live. Multiple processes can
append to the same file; one write() per line keeps the lines whole.
"""
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

_quiet = False
_captured: list[str] | None = None
_seq = 0
_HERE = Path(__file__).resolve()
_PAYLOAD_LIMIT = 200_000
_ROOT_MARKERS = (".git", "pyproject.toml")


def quiet(on: bool = True) -> None:
    """Silence the flow log (handy around setup noise in tests)."""
    global _quiet
    _quiet = on


def _emit(role: str, text: str) -> None:
    line = f"[{role:<6}] {text}"
    if _captured is not None:
        _captured.append(line)
    if not _quiet:
        print(line, file=sys.stdout, flush=True)


@contextmanager
def capture():
    """Collect the lines logged inside the block (they are still printed). Used by tests."""
    global _captured
    previous, _captured = _captured, []
    try:
        yield _captured
    finally:
        _captured = previous


def send(role: str, target: str, text: str, *, kind: str = "", payload=None, depth: int = 1) -> None:
    _emit(role, f"--> {target:<7} {text}")
    _trace(role, "send", target, text, kind, payload, depth)


def recv(role: str, source: str, text: str, *, kind: str = "", payload=None, depth: int = 1) -> None:
    _emit(role, f"<-- {source:<7} {text}")
    _trace(role, "recv", source, text, kind, payload, depth)


def note(role: str, text: str, *, kind: str = "", payload=None, depth: int = 1) -> None:
    _emit(role, f"    {text}")
    _trace(role, "note", "", text, kind, payload, depth)


def event(role: str, direction: str, peer: str, text: str, *, kind: str = "", payload=None, depth: int = 1) -> None:
    """Trace only, never printed. For a process whose stdout is a protocol channel
    (e.g. an MCP server on stdio), use this instead of send/recv/note so the trace
    doesn't collide with that channel.

    `depth` lets a thin wrapper (one call, no branching, always the same shape)
    attribute the event to ITS caller instead of itself: depth=2 skips the
    wrapper's own frame too. A wrapper that branches or does real work should
    not use this; the trace would point past what actually decided to log.
    """
    _trace(role, direction, peer, text, kind, payload, depth)


def rule(title: str = "") -> None:
    """A separator line, handy between scenarios in tests or demos."""
    if not _quiet:
        print(f"\n---- {title} " + "-" * max(0, 70 - len(title)), flush=True)
    _trace("TEST", "rule", "", title, "rule", None)


def short(value, limit: int = 110) -> str:
    """Compact one-line rendering of arguments or results for the log."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --- structured trace (FLOWLOG_TRACE) -------------------------------------------

def _repo_root(start: Path) -> Path:
    """FLOWLOG_ROOT override, else walk up from `start` for a .git/pyproject.toml
    marker, else cwd, else `start` itself (relative_to then just fails over to
    the raw absolute path in _caller, which is fine)."""
    override = os.environ.get("FLOWLOG_ROOT")
    if override:
        return Path(override).resolve()
    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate
    return Path.cwd()


def _caller(depth: int = 1) -> dict:
    """First frame outside this file (then `depth - 1` more, for a logging wrapper's own caller)."""
    frame = sys._getframe(1)
    while frame and Path(frame.f_code.co_filename).resolve() == _HERE:
        frame = frame.f_back
    for _ in range(depth - 1):
        if frame is None or frame.f_back is None:
            break
        frame = frame.f_back
    if frame is None:
        return {}
    path = Path(frame.f_code.co_filename).resolve()
    try:
        shown = str(path.relative_to(_repo_root(path)))
    except ValueError:
        shown = str(path)
    return {"file": shown, "line": frame.f_lineno, "func": frame.f_code.co_name}


def _trace(role: str, direction: str, peer: str, text: str, kind: str, payload, depth: int = 1) -> None:
    path = os.environ.get("FLOWLOG_TRACE")
    if not path:
        return
    global _seq
    _seq += 1
    record = {
        "ts": time.time(), "pid": os.getpid(), "seq": _seq,
        "role": role, "dir": direction, "peer": peer, "text": text, "kind": kind,
        "code": _caller(depth),
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, default=str)
        if len(body) > _PAYLOAD_LIMIT:
            record["payload"] = {"truncated": True, "chars": len(body), "head": body[:_PAYLOAD_LIMIT]}
        else:
            record["payload"] = json.loads(body)
    data = (json.dumps(record, ensure_ascii=False, default=str) + "\n").encode()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
    except OSError:
        pass  # a broken trace file must never break the traced app
