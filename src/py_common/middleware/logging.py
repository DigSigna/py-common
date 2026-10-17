import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uuid

from py_common.core.logger import get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request/response as a structured JSON line.

    Takes service_name explicitly: the original per-service copy of this
    file hardcoded `get_logger("api-gateway")` at module level with a
    comment claiming "este nombre se sobreescribirá por servicio" — it
    never was, so every request log line from both certificate-service and
    signing-service was mislabeled `"service": "api-gateway"`. Fixed here
    by requiring the real service name at construction time instead of a
    module-level singleton.
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self._logger = get_logger(service_name)

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        start_time = time.time()

        self._logger.info(
            f"Request started: {request.method} {request.url.path}",
            action="request_start",
            correlation_id=correlation_id,
            method=request.method,
            path=str(request.url.path),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            self._logger.info(
                f"Request completed: {request.method} {request.url.path}",
                action="request_complete",
                correlation_id=correlation_id,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as exc:
            process_time = time.time() - start_time

            self._logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(exc)}",
                action="request_error",
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
                process_time_ms=round(process_time * 1000, 2),
            )
            raise
