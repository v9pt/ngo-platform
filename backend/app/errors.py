"""One error shape for the whole API: RFC 7807 application/problem+json.

Validation errors list which fields failed and why, but never echo the submitted values
(they may contain passwords or PAN).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")

PROBLEM_JSON = "application/problem+json"


def problem(status: int, title: str, detail: str | None = None, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        headers = dict(exc.headers) if exc.headers else None
        response = problem(exc.status_code, _title(exc.status_code), str(exc.detail))
        if headers:
            response.headers.update(headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return problem(422, "Validation failed", errors=errors)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # Log the real cause; return nothing that helps an attacker.
        log.exception("unhandled error", exc_info=exc)
        return problem(500, "Internal server error")


def _title(status: int) -> str:
    return {
        400: "Bad request",
        401: "Authentication required",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        429: "Too many requests",
    }.get(status, "Error")
