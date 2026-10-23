from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from py_common.core.request_context import HEADER_X_CORRELATION_ID, get_context_values
from .entities import AuditEvent
from .ports import AuditTransporter

# Header que lleva la API key estática de servicio para autenticar contra
# POST /api/v1/events de audit-service (ver
# platform-infra/docs/service-key-map.md para cómo se genera y distribuye).
# Deliberadamente distinto de Authorization/Bearer (JWT de usuario): son dos
# mecanismos de auth distintos, mezclarlos confundiría el AuthMiddleware de
# audit-service cuando valide este header. Mismo nombre que go-common's
# HeaderXServiceAPIKey.
HEADER_X_SERVICE_API_KEY = "X-Service-API-Key"


class HttpAuditTransporter(AuditTransporter):
    """Cliente HTTP para enviar eventos de auditoría a audit-service."""

    def __init__(
        self,
        base_url: str,
        service_name: str,
        api_key: Optional[str] = None,
        timeout: int = 10,
        logger: Optional[Any] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"{service_name}/1.0",
                "Content-Type": "application/json",
            }
        )

        # No es fatal (el circuit breaker/fallback a DB del hybrid processor
        # debe seguir funcionando aunque todavía no haya key configurada) —
        # sólo un error claro, una vez, acá al construir el cliente. Sin key,
        # send() simplemente manda la request sin el header y audit-service
        # la rechazará cuando su AuthMiddleware la valide; ese rechazo se
        # maneja igual que cualquier otro fallo de transporte.
        if not api_key and logger is not None:
            logger.error(
                "audit HTTP transporter: AUDIT_API_KEY no está configurada — "
                "las requests a audit-service se mandarán sin el header "
                f"{HEADER_X_SERVICE_API_KEY}",
                action="audit_api_key_missing",
            )

    def send(self, ctx: Any, event: AuditEvent) -> None:
        correlation_id = _resolve_correlation_id(ctx)
        headers: Dict[str, str] = {}
        if correlation_id:
            headers[HEADER_X_CORRELATION_ID] = correlation_id
        if self.api_key:
            headers[HEADER_X_SERVICE_API_KEY] = self.api_key

        payload = _serialize_event(event)
        url = f"{self.base_url}/api/v1/events"

        try:
            response = self.session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Error enviando evento de auditoría: {exc}")

    def health_check(self, ctx: Any) -> None:
        url = f"{self.base_url}/health"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Error en health check: {exc}")


def _serialize_event(event: AuditEvent) -> Dict[str, Any]:
    if hasattr(event, "dict") and callable(event.dict):
        return event.dict()
    if hasattr(event, "model_dump") and callable(event.model_dump):
        return event.model_dump()
    return event.__dict__


def _resolve_correlation_id(ctx: Any) -> str:
    if ctx is not None:
        if hasattr(ctx, "correlation_id"):
            return getattr(ctx, "correlation_id")
        if isinstance(ctx, dict):
            return str(ctx.get("correlation_id", ""))

    return get_context_values().correlation_id
