# Contributing

## Dev setup

```bash
uv sync --extra dev
uv run pytest
```

## Design constraints (please read before proposing a change here)

- **Manual API only.** `send/recv/note/event/rule` stay explicit calls you
  write yourself - there's no auto-instrumenting decorator in core, and PRs
  adding one won't be merged without a prior issue reaching agreement on it
  first. This was a deliberate v1 decision, not an oversight.
- **Core stays dependency-free.** The `flowlog` package itself (not the
  `hooks/` helpers, which have their own optional extras) must never gain a
  required runtime dependency.
- **The viewer has no built-in vocabulary.** Any `role`/`kind`/`peer`
  mapping belongs in a project's own `flowlog.config.json`, not hardcoded
  into the viewer's JS. See `docs/config-schema.md`.

## Multi-language ports

flowlog explicitly invites ports to other languages. See the "Language
port" issue template. The **JSONL trace format** - not the Python API - is
the cross-language contract: a port's emitter just needs to produce the same
per-line JSON shape (documented in `docs/instrumentation-conventions.md` and
`docs/config-schema.md`) so the existing Python viewer works against it
unmodified.

Each port should use its own ecosystem's native production-build
elimination mechanism for a "ship without flowlog in prod" option -
`__debug__`/`-O` for Python, bundler flag guards (e.g.
`if (process.env.NODE_ENV !== 'production')`) for TS/JS, build tags
(`//go:build trace`) for Go, feature flags (`cfg!(feature = "trace")`) for
Rust - rather than inventing a new mechanism. Python's core doesn't need one
of its own beyond the env-var toggle, since that's already zero-cost when
off.

## Pull requests

Use the PR template's checklist. Small, focused PRs preferred - this is a
small tool on purpose.
