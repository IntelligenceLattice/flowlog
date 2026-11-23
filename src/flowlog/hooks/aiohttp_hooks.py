"""Opt-in aiohttp capture helper. You wire this in explicitly - flowlog never
monkeypatches aiohttp.

    import aiohttp
    from flowlog.hooks.aiohttp_hooks import build_trace_config

    async with aiohttp.ClientSession(trace_configs=[build_trace_config(role="HTTP")]) as session:
        await session.get("https://example.com")

Capture happens via aiohttp's own TraceConfig callbacks, on the plaintext
request/response objects at the application layer - see docs/hooks.md for
the capture-boundary note shared by all these helpers.
"""
import aiohttp

import flowlog

_HIDDEN_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _safe_headers(headers) -> dict:
    return {k: ("***" if k.lower() in _HIDDEN_HEADERS else v) for k, v in dict(headers).items()}


def build_trace_config(role: str = "HTTP", peer: str = "SERVER") -> "aiohttp.TraceConfig":
    config = aiohttp.TraceConfig()

    async def on_request_start(session, context, params) -> None:
        flowlog.send(role, peer, f"{params.method} {params.url.path}", kind="wire_request",
                     payload={"http": {"method": params.method, "url": str(params.url),
                                        "headers": _safe_headers(params.headers)}})

    async def on_request_end(session, context, params) -> None:
        resp = params.response
        flowlog.recv(role, peer, f"{resp.status} {resp.headers.get('content-type', '-')}",
                     kind="wire_response",
                     payload={"http": {"status": resp.status, "headers": _safe_headers(resp.headers)}})

    config.on_request_start.append(on_request_start)
    config.on_request_end.append(on_request_end)
    return config
