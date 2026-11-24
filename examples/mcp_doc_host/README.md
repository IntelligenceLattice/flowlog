# Example: MCP doc host

A standalone toy script (`toy_host.py`) that shows Flowlog tracing an MCP
host, client, and server, with no MCP SDK, cloud services, or vector
database to install. Everything runs in one process with a few short sleeps,
so you can see the viewer working in seconds.

## Run it

```bash
pip install git+https://github.com/IntelligenceLattice/flowlog
./run_demo.sh "How do I rotate an API key?"
```

or directly:

```bash
flowlog run --config flowlog.config.json toy_host.py -- "How do I rotate an API key?"
```

## What you're looking at

Seven lanes: **You** (caller) → **Agent** (host) → **Model** (LLM) →
**Connector** (client) → **HTTP wire** → **Doc server** → **Data sources**.
`flowlog.config.json` maps each `kind` string the script uses (`discover`,
`tool_call`, `llm_answer_request`, ...) to a phase band and a plain-language
tooltip, so clicking an arrow explains itself.

## A note on fidelity

This config drives Flowlog's **generic** rendering engine: lanes by role,
arrows by send/recv direction, phase bands and tooltips from config. There
is no per-project JavaScript, so you can point the same viewer at your own
system just by writing your own `flowlog.config.json`.
