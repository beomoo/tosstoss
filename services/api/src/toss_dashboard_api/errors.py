from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from toss_dashboard_api.contracts.responses import ErrorBody, ErrorEnvelope

logger = logging.getLogger("toss_dashboard_api.errors")


class AppError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.safe_message = message


class NotFoundError(AppError):
    def __init__(self, resource: str) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message=f"{resource} was not found")


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Required fixture data is unavailable") -> None:
        super().__init__(status_code=503, code="SERVICE_UNAVAILABLE", message=message)


def request_id_for(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def route_template_for(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) and template.startswith("/") else "<unmatched>"


def error_response(*, status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    body = ErrorEnvelope(
        contract_version="0.1.0",
        error=ErrorBody(code=code, message=message),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers={"x-request-id": request_id},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "request_failed",
        extra={
            "request_id": request_id_for(request),
            "error_code": exc.code,
            "stage": "request",
            "source": "application_error_handler",
            "method": request.method,
            "path": route_template_for(request),
            "status_code": exc.status_code,
        },
    )
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.safe_message,
        request_id=request_id_for(request),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "request_failed",
        extra={
            "request_id": request_id_for(request),
            "error_code": "INTERNAL_ERROR",
            "stage": "request",
            "source": "unhandled_exception_handler",
            "method": request.method,
            "path": route_template_for(request),
            "status_code": 500,
        },
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="The request could not be completed",
        request_id=request_id_for(request),
    )
