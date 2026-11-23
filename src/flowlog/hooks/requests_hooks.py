"""Opt-in `requests` capture helper. You wire this in explicitly - flowlog
never monkeypatches requests.

requests only exposes a response hook natively, so request-side capture needs
a thin wrapper around Session.send. Both run on plaintext Request/Response
objects at the application layer - see docs/hooks.md and httpx_hooks.py for
the capture-boundary note shared by all these helpers.

    import requests
    from flowlog.hooks.requests_hooks import traced_session

    session = traced_session(requests.Session(), role="HTTP")
    session.get("https://example.com")
"""
import flowlog

_HIDDEN_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _safe_headers(headers) -> dict:
    return {k: ("***" if k.lower() in _HIDDEN_HEADERS else v) for k, v in dict(headers).items()}


def traced_session(session, role: str = "HTTP", peer: str = "SERVER"):
    """Wraps session.send so every request/response pair is traced. Returns
    the same session object (mutated), for convenient chaining."""
    original_send = session.send

    def send(request, **kwargs):
        flowlog.send(role, peer, f"{request.method} {request.url}", kind="wire_request",
                     payload={"http": {"method": request.method, "url": request.url,
                                        "headers": _safe_headers(request.headers)}})
        response = original_send(request, **kwargs)
        flowlog.recv(role, peer, f"{response.status_code} {response.headers.get('content-type', '-')}",
                     kind="wire_response",
                     payload={"http": {"status": response.status_code, "headers": _safe_headers(response.headers)}})
        return response

    session.send = send
    return session
