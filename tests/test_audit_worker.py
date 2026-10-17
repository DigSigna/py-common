import pytest

from py_common.audit.entities import ActorType, AuditData
from py_common.audit.ports import AuditRecorder
from py_common.audit.worker import AuditWorker, WorkerConfig
from py_common.auth.identity_context import IdentityContext
from py_common.auth.owner_type import OwnerType
from py_common.core.request_context import ContextValues, set_context_values


class _RecordingRecorder(AuditRecorder):
    def __init__(self):
        self.events = []

    async def record_event(self, ctx, event):
        self.events.append(event)


def _identity() -> IdentityContext:
    return IdentityContext(
        tenant_id="11111111-1111-1111-1111-111111111111",
        owner_type=OwnerType.USER,
        owner_id="owner-1",
        user_id="22222222-2222-2222-2222-222222222222",
        cert_level=0,
        max_cert_level=0,
        can_certify=False,
        certification_path="",
    )


@pytest.mark.asyncio
async def test_audit_operation_dispatches_built_event():
    set_context_values(
        ContextValues(
            correlation_id="corr-1",
            session_id="",
            ip_address="127.0.0.1",
            user_agent="pytest",
            request_id="req-1",
            actor="jwt:abcd...wxyz",
        )
    )
    recorder = _RecordingRecorder()
    worker = AuditWorker(recorder, config=WorkerConfig(worker_count=1))

    data = AuditData(
        service_name="certificate-service",
        event_type="CERTIFICATE",
        operation="ISSUE_CERTIFICATE",
        resource_id="",
        resource_type="certificate",
        actor_type=ActorType.USER.value,
        success=True,
        status_code="200",
        err_msg="",
        duration_ms=12,
        metadata={},
    )
    await worker.audit_operation(None, data, _identity())
    await worker._queue.join()  # deterministic wait for the worker to drain it

    assert len(recorder.events) == 1
    event = recorder.events[0]
    assert event.service_name == "certificate-service"
    assert event.event_action == "ISSUE_CERTIFICATE"
    assert str(event.tenant_id) == "11111111-1111-1111-1111-111111111111"

    await worker.close()


@pytest.mark.asyncio
async def test_audit_operation_without_client_is_noop():
    worker = AuditWorker(None)

    await worker.audit_operation(
        None,
        AuditData(
            service_name="x",
            event_type="x",
            operation="x",
            resource_id="",
            resource_type="x",
            actor_type="USER",
            success=True,
            status_code="200",
            err_msg="",
            duration_ms=0,
            metadata={},
        ),
        None,
    )
    await worker.close()


@pytest.mark.asyncio
async def test_close_is_idempotent_without_client():
    worker = AuditWorker(None)
    await worker.close()
    await worker.close()
