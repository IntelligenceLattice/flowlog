<!--
Copilot has no native "/command-from-file" mechanism like Claude Code's
custom slash commands, so this is phrased as durable repo instructions
instead of a one-shot command: copy this block into your project's
.github/copilot-instructions.md (merge with whatever is already there -
don't overwrite the file). It then applies implicitly whenever Copilot
touches files in this repo, rather than being invoked on demand.
-->

## flowlog instrumentation

When asked to instrument this codebase with flowlog tracing (or to add
tracing/observability using flowlog), follow these steps exactly:

1. Detect the target scope (a file, a folder, or the whole repo if none is given).
2. Ensure `flowlog` is installed in this project. Check `import flowlog`; if
   missing, detect this project's dependency convention (uv/poetry
   pyproject, requirements.txt, or bare pip) and install flowlog the
   matching way, as the PyPI package `flowlog-trace` (not `flowlog`, which is an unrelated project). Prefer a dev-only dependency group, since instrumented
   calls are wrapped in `if __debug__:`.
3. Identify instrumentation points: function entry/exit at process/network
   boundaries, request handlers, tool/queue dispatch - not every function,
   only places where something crosses a boundary worth seeing on a flow
   diagram.
4. Insert `flowlog.send/recv/note` calls using this project's own
   role/kind/peer vocabulary. Ask what to call a role/kind if it's not
   obvious from existing module/folder names - don't guess silently.
5. Wrap every inserted call as `if __debug__: flowlog.send(...)` with
   `import flowlog` lazily inside the guard, not at module top.
6. Write or update `flowlog.config.json` at the scope root so its lanes
   match the roles just used.
7. Don't add try/except around flowlog calls - they're already safe no-ops
   on error.
8. Show the full diff for review. Do not commit automatically.
