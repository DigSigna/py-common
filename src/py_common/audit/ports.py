from abc import ABC, abstractmethod
from typing import Any, Optional

from py_common.auth.identity_context import IdentityContext
from .entities import AuditData, AuditEvent


class AuditStorage(ABC):
    @abstractmethod
    def store_audit_record(self, record: AuditEvent) -> None:
        """Store an audit record"""
        pass


# Client to send audit events to an external system (kafka, logstash, http
# endpoint, etc.)
class AuditTransporter(ABC):
    @abstractmethod
    def send(self, ctx, event: AuditEvent):
        """Envía un evento de auditoría a un sistema externo."""
        pass

    @abstractmethod
    def health_check(self, ctx):
        """Realiza una comprobación de salud del sistema externo."""
        pass


class AuditRecorder(ABC):
    @abstractmethod
    async def record_event(self, ctx: Any, event: AuditEvent) -> None:
        """Registra un evento de auditoría."""
        raise NotImplementedError


class AuditEventDispatcher(ABC):
    @abstractmethod
    async def audit_operation(
        self, ctx: Any, data: AuditData, identity_context: Optional[IdentityContext]
    ) -> None:
        """Dispatch an audit event to the appropriate recorder(s).

        identity_context es opcional: operaciones a nivel de infraestructura
        (p. ej. un decorator de repositorio) no tienen un IdentityContext de
        request real.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any resources held by the dispatcher"""
        pass
