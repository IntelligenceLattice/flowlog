#!/usr/bin/env python3
"""Remove flowlog instrumentation from Python sources for a production build.

Deletes, using the AST (so multi-line calls are handled correctly):
  * ``import flowlog`` / ``from flowlog import ...`` statements
  * bare ``flowlog.<anything>(...)`` statements
  * ``if __debug__:`` blocks whose body is only flowlog code
  * comment lines tagged ``# flowlog:`` (the "why this trace is here" notes)

Everything else is left byte-for-byte untouched.

Usage:
    python strip_flowlog.py FILE_OR_DIR [...]            # rewrite in place
    python strip_flowlog.py --check FILE_OR_DIR [...]    # exit 1 if anything would change
    python strip_flowlog.py --stdout FILE                # print stripped source
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

TAG = re.compile(r"^\s*#\s*flowlog:")


def _is_flowlog_stmt(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return all(a.name == "flowlog" or a.name.startswith("flowlog.") for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] == "flowlog"
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        f = node.value.func
        while isinstance(f, ast.Attribute):
            f = f.value
        return isinstance(f, ast.Name) and f.id == "flowlog"
    if (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
            and node.test.id == "__debug__" and not node.orelse):
        return all(_is_flowlog_stmt(s) for s in node.body)
    return False


def strip_source(src: str) -> str:
    tree = ast.parse(src)
    drop: set[int] = set()  # 1-based line numbers
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody", "handlers"):
            seq = getattr(node, field, None)
            if not isinstance(seq, list):
                continue  # e.g. Lambda.body / IfExp.body are expressions
            for stmt in seq:
                if isinstance(stmt, ast.stmt) and _is_flowlog_stmt(stmt):
                    drop.update(range(stmt.lineno, stmt.end_lineno + 1))
    lines = src.splitlines(keepends=True)
    drop.update(i + 1 for i, line in enumerate(lines) if TAG.match(line))
    out = [line for i, line in enumerate(lines, 1) if i not in drop]
    result = "".join(out)
    # A block emptied by stripping would no longer compile; fail loudly instead.
    ast.parse(result)
    return result


def _files(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for p in map(Path, paths):
        found.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return [f for f in found if f.resolve() != Path(__file__).resolve()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only; exit 1 if changes needed")
    mode.add_argument("--stdout", action="store_true", help="print result instead of rewriting")
    args = ap.parse_args(argv)

    dirty = 0
    for f in _files(args.paths):
        src = f.read_text(encoding="utf-8")
        new = strip_source(src)
        if args.stdout:
            sys.stdout.write(new)
            continue
        if new == src:
            continue
        dirty += 1
        if args.check:
            print(f"would strip: {f}")
        else:
            f.write_text(new, encoding="utf-8")
            print(f"stripped: {f}")
    return 1 if (args.check and dirty) else 0


if __name__ == "__main__":
    sys.exit(main())
