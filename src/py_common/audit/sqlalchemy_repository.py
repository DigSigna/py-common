import json
from uuid import UUID

from sqlalchemy import String, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from py_common.core.logger import get_logger
from py_common.db import Base
from .ports import AuditStorage
from .entities import AuditEvent as AuditEventDTO

logger = get_logger("audit-repository")


class AuditEvent(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=True)

    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    event_action: Mapped[str] = mapped_column(String(255), nullable=False)

    organization_id: Mapped[str] = mapped_column(String(36), nullable=True)
    # Nullable here to match the real schema: tenant_id's FK is
    # ON DELETE SET NULL (anonymous callers have none) and user_id has no
    # FK/NOT NULL constraint in the DB at all. Was `nullable=False` with
    # worker.py fabricating a random UUID to satisfy it — that just moved
    # the problem to tenant_id's FK instead of fixing it.
    user_id: Mapped[str] = mapped_column(String(36), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(255), nullable=True)

    actor_type: Mapped[str] = mapped_column(String(50), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=True)

    success: Mapped[bool] = mapped_column(nullable=False)
    status_code: Mapped[str] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str] = mapped_column(String(1024), nullable=True)

    duration_ms: Mapped[int] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=True)

    metadata_json: Mapped[str] = mapped_column("metadata", String(2048), nullable=True)


class SQLAlchemyAuditRepository(AuditStorage):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def store_audit_record(self, record: AuditEventDTO) -> None:
        stmt = insert(AuditEvent).values(
            id=str(record.id),
            correlation_id=_to_str(record.correlation_id),
            session_id=_to_str(record.session_id),
            request_id=_to_str(record.request_id),
            service_name=record.service_name,
            event_type=record.event_type,
            event_action=record.event_action,
            tenant_id=_to_str(record.tenant_id),
            organization_id=_to_str(record.organization_id),
            user_id=_to_str(record.user_id),
            resource_id=_to_str(record.resource_id),
            resource_type=record.resource_type,
            actor_type=getattr(record.actor_type, "value", record.actor_type),
            actor_id=_to_str(record.actor_id),
            success=record.success,
            status_code=record.status_code,
            error_message=record.error_message,
            duration_ms=record.duration_ms,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            metadata_json=json.dumps(record.metadata or {}),
        )
        try:
            await self._session.execute(stmt)
            await self._session.commit()
            logger.info(
                "Audit record inserted",
                action="audit_insert",
                event_type=record.event_type,
                event_action=record.event_action,
                record_id=str(record.id),
            )
        except Exception as exc:
            await self._session.rollback()
            logger.error(
                "Audit record insert failed",
                action="audit_insert_error",
                error=str(exc),
                record_id=str(record.id),
            )
            raise


def _to_str(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return str(value)
