from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .releases import ReleaseError


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any,
    legacy_detail: Any,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": legacy_detail,
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request.state.request_id,
            },
        },
    )


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(ReleaseError)
    async def release_error_handler(
        request: Request, exc: ReleaseError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            legacy_detail={"code": exc.code, "message": exc.message, **exc.details},
        )

    @application.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code", f"http_{exc.status_code}"))
            message = str(exc.detail.get("message", code.replace("_", " ")))
            details = exc.detail.get("details", {})
        else:
            code = f"http_{exc.status_code}"
            message = str(exc.detail)
            details = {}
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
            legacy_detail=exc.detail,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        issues = exc.errors()
        return error_response(
            request,
            status_code=422,
            code="request_validation_failed",
            message="Request validation failed",
            details={"issues": issues},
            legacy_detail=issues,
        )
