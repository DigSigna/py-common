from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from py_common.core.logger import get_logger
from py_common.core.request_context import get_context_values
from py_common.errors import DomainError


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Maps DomainError subclasses to a consistent HTTP error response.

    Takes service_name explicitly — the original per-service copy of this
    file hardcoded get_logger("certificate-service")/get_logger(
    "signing-service") at module level, the one line that actually
    differed between the two repos' otherwise-identical copy.
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self._logger = get_logger(service_name)

    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except DomainError as exc:
            self._logger.warning(
                f"Domain error: {exc.code}",
                action="domain_error",
                correlation_id=get_context_values().correlation_id,
                path=str(request.url.path),
                error_code=exc.code,
            )
            return JSONResponse(
                status_code=exc.http_status, content={"error": exc.to_dict()}
            )
        except Exception as exc:
            self._logger.error(
                f"Unhandled exception: {exc}",
                action="unhandled_exception",
                correlation_id=get_context_values().correlation_id,
                path=str(request.url.path),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal Server Error",
                        "details": {},
                    }
                },
            )
