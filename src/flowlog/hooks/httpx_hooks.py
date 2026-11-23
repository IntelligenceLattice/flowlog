"""Opt-in httpx capture helper. You wire this in explicitly - flowlog never
monkeypatches httpx.

    import httpx
    from flowlog.hooks.httpx_hooks import build_event_hooks

    client = httpx.AsyncClient(event_hooks=build_event_hooks(role="HTTP"))
    # for a sync httpx.Client, write sync versions of on_request/on_response instead

Capture happens on the httpx Request/Response *objects*, at the application
layer: for an outgoing request this runs after httpx has built the request
but before TLS encrypts anything on the wire; for an incoming response this
runs after httpx (and TLS) have already decrypted it. flowlog never inspects
wire bytes and cannot decode traffic it isn't handed by the app layer - see
docs/hooks.md. By convention the viewer renders role="HTTP" rows in a
thinner "wire" style; use that role unless you have a reason not to.
"""
import json

import flowlog

_HIDDEN_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _safe_headers(headers) -> dict:
    return {k: ("***" if k.lower() in _HIDDEN_HEADERS else v) for k, v in headers.items()}


def build_event_hooks(role: str = "HTTP", peer: str = "SERVER") -> dict:
    """Returns {"request": [...], "response": [...]} for httpx.Client(event_hooks=...)."""

    async def on_request(request) -> None:
        try:
            body = json.loads(request.content) if request.content else None
        except (ValueError, TypeError):
            body = None
        flowlog.send(
            role, peer, f"{request.method} {request.url.path}",
            kind="wire_request",
            payload={"http": {"method": request.method, "url": str(request.url),
                               "headers": _safe_headers(request.headers)}, "body": body},
        )

    async def on_response(response) -> None:
        content_type = response.headers.get("content-type", "").split(";")[0]
        payload = {"http": {"status": response.status_code, "headers": _safe_headers(response.headers)}}
        flowlog.recv(role, peer, f"{response.status_code} {content_type or '-'}",
                     kind="wire_response", payload=payload)

    return {"request": [on_request], "response": [on_response]}
