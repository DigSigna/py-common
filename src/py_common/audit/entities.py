from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class ActorType(str, Enum):
    USER = "USER"
    SERVICE = "SERVICE"
    SYSTEM = "SYSTEM"
    EXTERNAL = "EXTERNAL"


class AuditStrategy(Enum):
    DATABASE = "database"
    HTTP = "http"
    HYBRID = "hybrid"
    MOCK = "mock"
    ASYNC = "async"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Verifica si una cadena es una estrategia de auditoría válida."""
        return value in cls._value2member_map_


@dataclass(frozen=True)
class AuditData:
    service_name: str
    event_type: str
    operation: str
    resource_id: str
    resource_type: str
    actor_type: str
    success: bool
    status_code: str
    err_msg: str
    duration_ms: int
    metadata: Dict[str, Any]


@dataclass
class AuditEvent:
    user_id: UUID
    tenant_id: UUID
    id: UUID
    correlation_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    request_id: Optional[UUID] = None

    service_name: str = ""
    event_type: str = ""
    event_action: str = ""

    organization_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[str] = None

    actor_type: Optional[ActorType] = None
    actor_id: Optional[UUID] = None

    success: bool = True
    status_code: Optional[str] = None
    error_message: Optional[str] = None

    duration_ms: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    metadata: Optional[dict] = None
