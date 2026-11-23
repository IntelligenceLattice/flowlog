# Capturing HTTP traffic

`flowlog.hooks` ships small, documented helpers for httpx, requests, and
aiohttp. You wire each one in explicitly:

```python
import httpx
from flowlog.hooks.httpx_hooks import build_event_hooks

client = httpx.AsyncClient(event_hooks=build_event_hooks(role="HTTP"))
```

```python
import requests
from flowlog.hooks.requests_hooks import traced_session

session = traced_session(requests.Session(), role="HTTP")
```

```python
import aiohttp
from flowlog.hooks.aiohttp_hooks import build_trace_config

async with aiohttp.ClientSession(trace_configs=[build_trace_config(role="HTTP")]) as session:
    ...
```

flowlog **never monkeypatches** these libraries. If you don't call one of
these helpers, nothing about your HTTP traffic is captured.

## Where capture actually happens - the encryption boundary

Each helper hooks into its library's own request/response lifecycle, on the
**plaintext application-layer object** - an `httpx.Request`/`Response`, a
`requests.Request`/`Response`, an aiohttp trace event:

- On the way out, the hook runs **after** your HTTP client has built the
  request but **before** TLS encrypts anything that leaves the process.
- On the way in, the hook runs **after** TLS has already decrypted the
  response and the client library has parsed it.

flowlog has no access to anything below that layer. It never inspects wire
bytes, never terminates or intercepts TLS, and cannot decode traffic it isn't
handed by the application layer. This is a deliberate scope boundary, not a
missing feature - for packet-level capture of encrypted traffic, reach for
Wireshark/tcpdump (which need their own TLS key access to be useful) instead.
flowlog answers "what did my code send and receive," not "what went over the
wire in encrypted form."

## Role convention

All three helpers default to `role="HTTP"`. The viewer renders that role in
a thinner "wire" row style (see [config-schema.md](config-schema.md)) - keep
using `"HTTP"` unless you have a specific reason to split wire traffic across
multiple roles.
