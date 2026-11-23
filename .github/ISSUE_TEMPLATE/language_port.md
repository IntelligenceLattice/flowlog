---
name: Language port
about: Port flowlog's core (JSONL emitter + caller capture) to another language
labels: language-port
---

**Target language**:

**Stdlib-only equivalent**: flowlog's Python core has zero pip dependencies.
What's the equivalent constraint in your target language's ecosystem (if any)?

**Trace-file interop**: the port must emit the same JSON shape per line
(`ts`, `pid`, `seq`, `role`, `dir`, `peer`, `text`, `kind`, `code`,
`payload` - see `docs/config-schema.md` and
`docs/instrumentation-conventions.md`) so the existing Python viewer works
against it unmodified. Confirm you've read that contract.

**Production-strip mechanism**: Python uses `__debug__`/`-O`. What's your
language's native build-time dead-code-elimination mechanism (bundler flag
guards, build tags, feature flags, ...)? See `CONTRIBUTING.md`.

**Maintenance**: do you intend to maintain this port long-term, or is this a
one-off contribution someone else should adopt?
