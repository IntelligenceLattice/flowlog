# Instrumentation conventions

The canonical procedure for instrumenting a codebase with flowlog - followed
by hand, or by an AI assistant via one of the `ai-assistants/` files (which
duplicate this body verbatim; keep them in sync if you edit this).

## Steps

1. **Detect scope.** A file, a folder, or the whole project if none given.
2. **Ensure `flowlog` is installed.** Check `import flowlog` succeeds. If
   not, detect the project's own dependency convention (uv/poetry
   `pyproject.toml`, `requirements.txt`, or bare pip) and install flowlog
   the matching way, as the PyPI package `flowlog-trace` (not `flowlog`, which is an unrelated project) - never introduce a new dependency mechanism. Prefer a
   dev-only dependency group, since instrumented calls are wrapped for the
   production-strip convention (step 4) and don't need flowlog installed in
   production at all. Verify with a second `import flowlog` check; stop and
   report the exact failure if it still fails rather than guessing further.
3. **Identify instrumentation points.** Function entry/exit at process or
   network boundaries, request handlers, tool/queue dispatch. Not every
   function - only places where something crosses a boundary worth seeing
   on a flow diagram.
4. **Insert the calls**, using the project's own role/kind/peer vocabulary -
   ask rather than guess when a role name isn't obvious from existing
   module/folder names:
   - `flowlog.send(role, target, text, kind=..., payload=...)` - outbound.
   - `flowlog.recv(role, source, text, kind=..., payload=...)` - inbound reply.
   - `flowlog.note(role, text, kind=...)` - standalone step.
   - `flowlog.event(role, direction, peer, text, kind=...)` - internal hop, or
     a process whose stdout is itself a protocol channel.

   Wrap every inserted call as:
   ```python
   if __debug__:
       import flowlog
       flowlog.send(...)
   ```
   with the import lazy, inside the guard, not at module top. This is the
   default convention so `python -O`/`PYTHONOPTIMIZE=1` strips flowlog
   entirely from a production build - see the main README's switches table.
5. **Write or update `flowlog.config.json`** at the scope's root so its
   lanes match the roles just used (see [config-schema.md](config-schema.md)).
6. **No extra error handling.** flowlog calls are already safe no-ops on
   failure - don't wrap them in try/except.
7. **Show a diff for review. Never auto-commit.**

## Picking `kind` strings

Short, consistent tokens. A request and its reply should use `kind`s you can
later pair in config (`pairs`), e.g. `"tool_call"` / `"tool_result"`. There's
no built-in vocabulary - pick what reads clearly for your own domain.

## Multi-language ports

This procedure (and the JSONL trace format it produces) is the
cross-language contract - not the Python API. A port to another language
should emit the same JSON shape per line (`ts`, `pid`, `seq`, `role`, `dir`,
`peer`, `text`, `kind`, `code`, `payload`) so the existing Python viewer
works against it unmodified. Each port should use its own ecosystem's
native production-build elimination mechanism for the same "ship without
flowlog in prod" result Python gets from `__debug__`/`-O`: bundler
dead-code-elimination guards for TS/JS, build tags for Go, feature flags for
Rust. See `CONTRIBUTING.md` and `ROADMAP.md`.
