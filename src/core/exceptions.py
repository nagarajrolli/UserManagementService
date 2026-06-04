"""
src/core/exceptions.py
-----------------------
Domain exceptions and global FastAPI exception handlers.

Concepts covered:
- Custom exception hierarchy: a base AppBaseException carries an HTTP status code
  so the generic handler can map any domain error to the right response — no
  HTTPException scattered throughout your business logic.
- register_exception_handlers(): called once in main.py; keeps main.py clean.
- Separation of concerns: routers raise domain exceptions; this module translates
  them to HTTP responses.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exception hierarchy
# ---------------------------------------------------------------------------

class AppBaseException(Exception):
    """
    Root for all application-level exceptions.
    Carries a human-readable message and the HTTP status code that maps to it.
    Services raise these; the global handler converts them to JSON responses.
    """

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UserNotFoundException(AppBaseException):
    def __init__(self, user_id: int):
        super().__init__(
            message=f"User with id={user_id} was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UserAlreadyExistsException(AppBaseException):
    def __init__(self, email: str):
        super().__init__(
            message=f"A user with email '{email}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidCredentialsException(AppBaseException):
    def __init__(self):
        # Intentionally vague — don't tell attackers which field was wrong.
        super().__init__(
            message="Invalid email or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class InactiveUserException(AppBaseException):
    def __init__(self):
        super().__init__(
            message="This account has been deactivated.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class PermissionDeniedException(AppBaseException):
    def __init__(self):
        super().__init__(
            message="You do not have permission to perform this action.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# Global handlers
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all global exception handlers to the FastAPI app instance.
    Call this once during app startup in main.py.

    Handler priority (most specific → least specific):
      AppBaseException → RequestValidationError → IntegrityError → Exception
    """

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
        """Converts any domain exception into a structured JSON error response."""
        logger.warning(
            "Domain exception | path=%s | status=%s | detail=%s",
            request.url.path,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Pydantic validation failures (wrong types, missing fields, constraint violations).
        Returns the full error list so clients know exactly what to fix.
        """
        logger.warning(
            "Validation error | path=%s | errors=%s",
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            # HTTP_422_UNPROCESSABLE_ENTITY was renamed in Starlette 1.x
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """
        SQLAlchemy DB-level integrity violations (e.g. unique constraint race condition).
        This is a safety net — the service layer should catch duplicates first.
        """
        logger.error(
            "DB integrity error | path=%s | error=%s",
            request.url.path,
            str(exc.orig),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "A database conflict occurred. The resource may already exist."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Last-resort catch-all. Logs the full traceback for debugging but returns a
        generic message to the client — never leak internal details in production.
        """
        logger.exception(
            "Unhandled exception | path=%s | error=%s",
            request.url.path,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )
