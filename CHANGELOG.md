# Changelog

## 0.1.1

- Package description now says Flowlog currently supports Python.
- PyPI page: install instructions use `pip install flowlog-trace`, and all
  README images and links point to GitHub so they display on PyPI.

## 0.1.0 - initial release

First public release: Flowlog's core API, viewer, CLI
(`run`/`view`/`init`/`doctor`), opt-in HTTP hooks, and AI-assistant
instrumentation prompts. The viewer's lane/phase/kind vocabulary lives in a
per-project `flowlog.config.json` rather than in code, and
`examples/mcp_doc_host/` shows a worked MCP example.
