from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Sequence

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from toss_dashboard_api.errors import error_response, route_template_for

logger = logging.getLogger("toss_dashboard_api.http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, allowed_hosts: Sequence[str]) -> None:
        super().__init__(app)
        self._allowed_hosts = frozenset(host.lower() for host in allowed_hosts)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        host_header = request.headers.get("host", "").strip().lower()
        host, separator, port = host_header.partition(":")
        host_is_valid = (
            bool(host)
            and host in self._allowed_hosts
            and (not separator or (port.isdigit() and 0 < int(port) <= 65535))
        )
        if not host_is_valid:
            logger.warning(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "error_code": "INVALID_HOST",
                    "stage": "request",
                    "source": "host_guard",
                    "method": request.method,
                    "path": "<unmatched>",
                    "status_code": 400,
                },
            )
            invalid_response = error_response(
                status_code=400,
                code="INVALID_HOST",
                message="The request host is not allowed",
                request_id=request_id,
            )
            invalid_response.headers["x-request-id"] = request_id
            return invalid_response
        started = time.perf_counter()
        response = await call_next(request)
        if (
            response.status_code == 400
            and request.method == "OPTIONS"
            and "access-control-request-method" in request.headers
        ):
            logger.warning(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "error_code": "INVALID_CORS",
                    "stage": "request",
                    "source": "cors_guard",
                    "method": request.method,
                    "path": route_template_for(request),
                    "status_code": 400,
                },
            )
            response = error_response(
                status_code=400,
                code="INVALID_CORS",
                message="The cross-origin request is not allowed",
                request_id=request_id,
            )
        response.headers["x-request-id"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": route_template_for(request),
                "status_code": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        return response
