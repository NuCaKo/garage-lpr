from collections.abc import Iterable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Apply small, deterministic browser hardening headers without BaseHTTP overhead."""

    _BASE_HEADERS = (
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    )
    _CONTENT_SECURITY_POLICY = (
        b"default-src 'self'; "
        b"base-uri 'self'; "
        b"connect-src 'self' ws: wss:; "
        b"form-action 'self'; "
        b"frame-ancestors 'none'; "
        b"img-src 'self' blob: data:; "
        b"object-src 'none'; "
        b"script-src 'self'; "
        b"style-src 'self'"
    )

    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        self._app = app
        self._production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._headers_for_path(str(scope.get("path", ""))))
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_headers)

    def _headers_for_path(self, path: str) -> Iterable[tuple[bytes, bytes]]:
        yield from self._BASE_HEADERS
        if path.startswith("/api/v1/auth"):
            yield b"cache-control", b"no-store"
        if self._production:
            yield b"content-security-policy", self._CONTENT_SECURITY_POLICY
