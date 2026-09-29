"""API error handlers mapping domain/validation errors to JSON responses (SYSTEM_DESIGN §10.1)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.features.pipeline.domain.errors import DomainError

logger = logging.getLogger(__name__)


def _format_validation_error(exc: RequestValidationError) -> tuple[str, list[dict[str, str]]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field_parts = [str(x) for x in loc if x not in ("body", "query", "path")]
        field_name = ".".join(field_parts) if field_parts else "request"
        msg = error.get("msg", "Invalid input")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        details.append({"field": field_name, "message": msg})

    first_msg = f"{details[0]['field']}: {details[0]['message']}" if details else "Invalid input"
    return first_msg, details


def register_error_handlers(app: FastAPI) -> None:
    """Register API error handlers on FastAPI application instance."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        if not request.url.path.startswith("/api/"):
            raise exc
        body: dict[str, Any] = {
            "code": exc.code,
            "message": exc.message,
        }
        if exc.hint is not None:
            body["hint"] = exc.hint
        return JSONResponse(status_code=exc.http_status, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> Any:
        if not request.url.path.startswith("/api/"):
            return await request_validation_exception_handler(request, exc)
        first_msg, details = _format_validation_error(exc)
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_INPUT",
                "message": first_msg,
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if not request.url.path.startswith("/api/"):
            raise exc
        logger.error(
            "Unhandled API exception path=%s type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "Something went wrong.",
            },
        )
