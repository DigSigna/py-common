"""Declarative base for the SQLAlchemy models this package ships
(audit_logs, idempotency_keys). Deliberately separate from each
consuming service's own Base (Tenant/Certificate/SigningRequest/etc.):
none of those tables declare a ForeignKey into audit_logs/idempotency_keys
or vice versa, and no consumer ever calls Base.metadata.create_all() (the
shared `digsigna` schema is managed by the separate `migrations` repo, not
by SQLAlchemy) — so there's no need for every model across every service
to share one registry.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
