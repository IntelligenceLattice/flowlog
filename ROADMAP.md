# Roadmap

Living list - not commitments, just where help is wanted. Open an issue
(see the "Language port" and "Feature request" templates) if you want to
pick one of these up.

## Language ports (candidates, none started yet)

- **Node/TS** - bundler-native production strip via
  `if (process.env.NODE_ENV !== 'production')` guards.
- **Go** - build tags (`//go:build trace`) for the production-strip
  equivalent.
- **Rust** - `cfg!(feature = "trace")` for the production-strip equivalent.

Any port's only hard requirement: emit the same JSONL line shape documented
in `docs/config-schema.md`, so the existing Python viewer works against it
unmodified. See `CONTRIBUTING.md`.

## Feature ideas (not yet scheduled)

- Windows-native CI verification (should work today - stdlib only - but
  isn't CI-checked yet).
- A `flowlog init` heuristic pass for languages beyond Python, once a port
  exists to scaffold for.

Pending feature ideas surfaced via issues get added here as they come in.
