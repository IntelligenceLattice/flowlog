---
description: Instrument code with flowlog tracing calls (installs flowlog if needed)
argument-hint: [path]
---

Target scope: $ARGUMENTS (a file, a folder, or omit for the whole repo).

Follow these steps exactly:
1. Detect scope from the argument above.
2. Ensure `flowlog` is installed in this project (check `import flowlog`; if missing,
   detect this project's dependency convention - uv/poetry pyproject, requirements.txt,
   or bare pip - and install flowlog the matching way,
   from `git+https://github.com/IntelligenceLattice/flowlog` (the PyPI package named `flowlog` is an unrelated project); prefer adding it as a
   dev-only dependency since instrumented calls will be wrapped in `if __debug__:`).
3. Identify instrumentation points in scope: function entry/exit at process/network
   boundaries, request handlers, tool/queue dispatch - not every function, only
   places where something crosses a boundary worth seeing on a flow diagram.
4. Insert `flowlog.send/recv/note` calls using this project's own role/kind/peer
   vocabulary. Ask me what to call a role/kind if it's not obvious from existing
   module/folder names - don't guess silently.
5. Wrap every inserted call as `if __debug__: flowlog.send(...)` with `import flowlog`
   lazily inside the guard, not at module top.
6. Write or update `flowlog.config.json` at the scope root so its lanes match the
   roles just used.
7. Don't add try/except around flowlog calls - they're already safe no-ops on error.
8. Show me a diff of everything you plan to change. Do not commit.
