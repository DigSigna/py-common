import pytest

from py_common.audit.entities import AuditStrategy
from py_common.audit.hybrid_processor import HybridProcessor
from py_common.audit.ports import AuditStorage, AuditTransporter


class _FakeStorage(AuditStorage):
    def __init__(self):
        self.stored = []

    def store_audit_record(self, record):
        self.stored.append(record)


class _FakeTransporter(AuditTransporter):
    def __init__(self, fail_times: int = 0):
        self.sent = []
        self._fail_times = fail_times

    def send(self, ctx, event):
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("transport down")
        self.sent.append(event)

    def health_check(self, ctx):
        return None


@pytest.mark.asyncio
async def test_database_strategy_always_stores():
    storage = _FakeStorage()
    processor = HybridProcessor(AuditStrategy.DATABASE, None, storage)

    await processor.record_event(None, "event-1")

    assert storage.stored == ["event-1"]


@pytest.mark.asyncio
async def test_http_strategy_without_primary_falls_back_to_storage():
    storage = _FakeStorage()
    processor = HybridProcessor(AuditStrategy.HTTP, None, storage)

    await processor.record_event(None, "event-1")

    assert storage.stored == ["event-1"]


@pytest.mark.asyncio
async def test_http_strategy_sends_via_primary():
    storage = _FakeStorage()
    transporter = _FakeTransporter()
    processor = HybridProcessor(AuditStrategy.HTTP, transporter, storage)

    await processor.record_event(None, "event-1")

    assert transporter.sent == ["event-1"]
    assert storage.stored == []


@pytest.mark.asyncio
async def test_hybrid_strategy_falls_back_on_send_failure():
    storage = _FakeStorage()
    transporter = _FakeTransporter(fail_times=1)
    processor = HybridProcessor(AuditStrategy.HYBRID, transporter, storage)

    await processor.record_event(None, "event-1")

    assert storage.stored == ["event-1"]


@pytest.mark.asyncio
async def test_hybrid_strategy_opens_circuit_after_max_failures():
    storage = _FakeStorage()
    transporter = _FakeTransporter(fail_times=10)
    processor = HybridProcessor(
        AuditStrategy.HYBRID, transporter, storage, max_failures=2
    )

    await processor.record_event(None, "event-1")
    await processor.record_event(None, "event-2")
    assert processor._circuit_open is True

    # Circuit now open: goes straight to storage without calling send again.
    transporter.sent.clear()
    await processor.record_event(None, "event-3")
    assert storage.stored == ["event-1", "event-2", "event-3"]


@pytest.mark.asyncio
async def test_hybrid_strategy_recovers_after_successful_send():
    storage = _FakeStorage()
    transporter = _FakeTransporter(fail_times=1)
    processor = HybridProcessor(AuditStrategy.HYBRID, transporter, storage)

    await processor.record_event(None, "event-1")  # fails, stores, +1 failure
    await processor.record_event(None, "event-2")  # succeeds, resets circuit

    assert transporter.sent == ["event-2"]
    assert processor._failures == 0
    assert processor._circuit_open is False
