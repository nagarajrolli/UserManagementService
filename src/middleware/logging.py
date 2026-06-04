"""
src/middleware/logging.py
--------------------------
HTTP request/response logging middleware.

Concepts covered:
- BaseHTTPMiddleware: Starlette's hook for wrapping every request.
  Subclass it and override dispatch(request, call_next).
- Request ID (correlation ID): a short UUID fragment attached to every request.
  Stored on request.state so any downstream code can reference it.
  Returned in the X-Request-ID response header so clients can correlate
  their logs with server-side logs in support tickets.
- Structured log format: key=value pairs are machine-parseable and work well
  with log aggregators like Datadog, CloudWatch, ELK Stack.
- perf_counter: higher-resolution timer than time.time(); ideal for sub-ms
  latency measurements.
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    For every HTTP request:
      1. Generate a short correlation ID and attach it to request.state.
      2. Time the full round-trip.
      3. Log method, path, status code, and duration.
      4. Return the correlation ID in the X-Request-ID response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Short 8-char UUID fragment — unique enough for correlation, not too noisy.
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "rid=%s method=%s path=%s status=%d duration=%.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Attach to response so clients can reference it in support tickets.
        response.headers["X-Request-ID"] = request_id
        return response
