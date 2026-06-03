"""Middleware components for FastAPI application."""
import time
import uuid
from typing import Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate and propagate X-Request-ID for distributed tracing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided ID or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind to logger context for this request
        request.state.request_id = request_id
        request_logger = logger.bind(request_id=request_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        return response


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status code, and duration for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "N/A")

        request_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )

        request_logger.info("Request started")

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            request_logger.info(
                f"Response: {response.status_code} in {process_time:.4f}s"
            )

            return response

        except Exception as exc:
            process_time = time.perf_counter() - start_time
            request_logger.error(
                f"Error after {process_time:.4f}s: {exc}",
                exc_info=True,
            )
            raise
