"""Domain exceptions and the single error envelope every response uses."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger()


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        self.message = message or self.code.replace("_", " ")
        self.details = details or {}
        super().__init__(self.message)


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class JobNotFound(NotFound):
    code = "job_not_found"


class AgentNotFound(NotFound):
    code = "agent_not_found"


class CandidateNotFound(NotFound):
    code = "candidate_not_found"


class CallNotFound(NotFound):
    code = "call_not_found"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class Unauthorized(AppError):
    status_code = 401
    code = "access_code_required"


class FeatureDisabled(AppError):
    status_code = 503
    code = "feature_disabled"


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_error"


class HunarApiError(UpstreamError):
    code = "hunar_api_error"

    def __init__(self, status: int, message: str, details: Any = None):
        super().__init__(message, details={"upstreamStatus": status, "upstream": details})
        self.upstream_status = status


class PeopleProviderError(UpstreamError):
    code = "people_provider_error"


class LlmError(UpstreamError):
    code = "llm_error"


class LlmCredentialRejected(LlmError):
    """The key exists but the provider will not honour it."""

    status_code = 503
    code = "llm_credential_rejected"


class LlmQuotaExhausted(LlmError):
    """Out of credit, or rate limited. Not a bug, and not something to paper over."""

    status_code = 503
    code = "llm_quota_exhausted"


def _envelope(
    code: str, message: str, request: Request, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(details or {})
    merged["requestId"] = getattr(request.state, "request_id", None)
    return {"error": {"code": code, "message": message, "details": merged}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log.warning("app_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, request, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": ".".join(str(p) for p in e.get("loc", [])), "msg": e.get("msg")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "validation_failed", "Request validation failed", request, {"errors": errors}
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code, content=_envelope(code, str(exc.detail), request)
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500, content=_envelope("internal_error", "Internal server error", request)
        )
