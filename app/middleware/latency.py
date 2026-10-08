import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

LATENCY_HEADER = b"x-scalepulse-latency-ms"


class LatencyHeaderMiddleware:
    """Pure ASGI middleware that stamps server-side latency on every HTTP response.

    Measures time until response headers are sent (body streaming time is not included).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter_ns()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                headers = list(message.get("headers", []))
                headers.append((LATENCY_HEADER, f"{elapsed_ms:.3f}".encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
