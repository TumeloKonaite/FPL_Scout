from __future__ import annotations

from urllib.parse import parse_qs

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.app.core.public_recommendation_timing import (
    correlation_id,
    emit_summary,
    finish_timing,
    start_timing,
)


class PublicRecommendationTimingMiddleware:
    """Emit one performance summary for the public recommendation endpoint."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not (
            scope["method"] == "GET" and scope["path"] == "/api/recommendations"
        ):
            await self.app(scope, receive, send)
            return

        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        season = query.get("season", [None])[0]
        raw_gameweek = query.get("gameweek", [None])[0]
        try:
            gameweek = int(raw_gameweek) if raw_gameweek is not None else None
        except ValueError:
            gameweek = None

        from starlette.requests import Request

        request = Request(scope)
        trace_id = correlation_id(request.headers, request.state)
        request.state.trace_id = trace_id
        timing, token = start_timing(
            trace_id=trace_id,
            season=season,
            gameweek=gameweek,
        )
        status_code = 500
        response_started = False

        async def send_with_trace_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                headers = list(message.get("headers", []))
                if not any(name.lower() == b"x-request-id" for name, _ in headers):
                    headers.append((b"x-request-id", trace_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        except Exception as exc:
            timing.mark_failure(timing.active_stage, exc, category="server_error")
            raise
        finally:
            # If no response started, the outer server error handler will return 500.
            emit_summary(timing, status_code if response_started else 500)
            finish_timing(token)
