"""`flowlog init`: scans a target project and writes starter scaffolding -
flowlog.config.json and a notes file listing candidate instrumentation
points. Never edits source files; that's the AI-assistant commands' job
(see ai-assistants/ and docs/instrumentation-conventions.md), done under
review, not auto-applied here.
"""
import ast
import sys
from pathlib import Path

_BOUNDARY_HINTS = (
    "request", "response", "call", "send", "recv", "receive", "publish", "consume",
    "handle", "dispatch", "fetch", "post", "get", "put", "delete", "connect", "listen",
)


def _candidate_functions(py_file: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(py_file.read_text(errors="replace"))
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name.lower()
            if any(hint in name for hint in _BOUNDARY_HINTS) and not name.startswith("_"):
                found.append((node.lineno, node.name))
    return found


def _top_level_packages(target: Path) -> list[str]:
    names = []
    for entry in sorted(target.iterdir()):
        if entry.is_dir() and (entry / "__init__.py").exists() and not entry.name.startswith((".", "_")):
            names.append(entry.name)
        elif entry.suffix == ".py" and entry.stem not in ("setup", "conftest") and not entry.name.startswith((".", "_")):
            names.append(entry.stem)
    return names[:8]  # keep the starter config small; the user curates from here


def _write_config(target: Path, force: bool) -> Path:
    config_path = target / "flowlog.config.json"
    if config_path.exists() and not force:
        raise FileExistsError(str(config_path))
    roles = _top_level_packages(target) or ["app"]
    lanes = [{"id": r.upper(), "name": r} for r in roles]
    import json

    config = {
        "lanes": lanes, "groups": [], "phases": {}, "kind_phase": {}, "pairs": {}, "explain": {},
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return config_path


def _write_notes(target: Path, candidates: dict[Path, list[tuple[int, str]]]) -> Path:
    notes_path = target / "FLOWLOG_INSTRUMENTATION_NOTES.md"
    lines = [
        "# flowlog instrumentation notes",
        "",
        "Candidate boundaries found by `flowlog init` (function entry/exit at process or",
        "network edges, request handlers, tool/queue dispatch). This is a starting point,",
        "not a prescription - skip anything that isn't really a boundary worth seeing on",
        "a flow diagram, and add ones this scan missed.",
        "",
        "Nothing here was written into your source. Add calls like:",
        "",
        "```python",
        "if __debug__:",
        "    import flowlog",
        "    flowlog.send(\"<ROLE>\", \"<TARGET>\", \"what this call does\", kind=\"<short_kind>\")",
        "```",
        "",
    ]
    if not candidates:
        lines.append("No obvious candidates found by name-based scanning. That's fine for a small")
        lines.append("project - instrument by hand at whatever boundaries matter, or point an")
        lines.append("AI-assistant prompt (see the flowlog README) at this project instead.")
    for path, funcs in candidates.items():
        if not funcs:
            continue
        lines.append(f"## {path}")
        for lineno, name in funcs:
            lines.append(f"- `{name}` at line {lineno}")
        lines.append("")
    notes_path.write_text("\n".join(lines) + "\n")
    return notes_path


def run_init(target_dir: Path, *, force: bool) -> int:
    target = target_dir.resolve()
    if not target.is_dir():
        print(f"flowlog: target directory not found: {target}", file=sys.stderr)
        return 1

    try:
        config_path = _write_config(target, force)
    except FileExistsError as exc:
        print(f"flowlog: {exc} already exists. Use --force to overwrite it.", file=sys.stderr)
        return 1

    candidates = {}
    for py_file in sorted(target.rglob("*.py")):
        if any(part.startswith(".") or part in ("venv", ".venv", "__pycache__") for part in py_file.parts):
            continue
        funcs = _candidate_functions(py_file)
        if funcs:
            candidates[py_file.relative_to(target)] = funcs

    notes_path = _write_notes(target, candidates)
    print(f"flowlog: wrote {config_path.relative_to(target)}")
    print(f"flowlog: wrote {notes_path.relative_to(target)} ({len(candidates)} file(s) with candidate boundaries)")
    return 0
