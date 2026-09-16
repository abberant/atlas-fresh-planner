"""Error responses. The client always gets a small, readable JSON object.

A stack trace is never sent to the client. Unexpected problems are logged on
the server and answered with a short message.
"""

from __future__ import annotations

import logging
from typing import Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.models import ValidationIssue
from app.planning.invariants import InvariantViolation

logger = logging.getLogger("atlas_fresh")


class WorkbookInvalid(Exception):
    """The workbook was read but its content is not usable. Nothing is planned."""

    def __init__(self, issues: Sequence[ValidationIssue]) -> None:
        self.issues = list(issues)
        super().__init__(f"{len(self.issues)} validation errors")


class DataUnavailable(Exception):
    """The input file itself is missing or unreadable on the server."""


class ValidationFailedResponse(BaseModel):
    error: str = "VALIDATION_FAILED"
    errors: list[ValidationIssue]


class ServerErrorResponse(BaseModel):
    error: str = "SERVER_ERROR"
    message: str


class BadRequestResponse(BaseModel):
    error: str = "BAD_REQUEST"
    message: str


def _server_error(message: str) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "SERVER_ERROR", "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(WorkbookInvalid)
    async def _workbook_invalid(_: Request, exc: WorkbookInvalid) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_FAILED",
                "errors": [issue.model_dump() for issue in exc.issues],
            },
        )

    @app.exception_handler(DataUnavailable)
    async def _data_unavailable(_: Request, exc: DataUnavailable) -> JSONResponse:
        logger.error("input data unavailable: %s", exc)
        return _server_error(str(exc))

    @app.exception_handler(InvariantViolation)
    async def _invariant_violation(_: Request, exc: InvariantViolation) -> JSONResponse:
        # A plan that breaks a hard limit must never be shown as valid.
        logger.error("invariant violation: %s", exc)
        return _server_error(
            "The plan broke a hard limit and was not returned. Please report this with "
            f"today's input file. Details: {'; '.join(item.name for item in exc.failures)}."
        )

    @app.exception_handler(RequestValidationError)
    async def _bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "BAD_REQUEST",
                "message": "The request body is not in the expected shape.",
            },
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected server error")
        return _server_error("Something went wrong on the server. Please try again.")
