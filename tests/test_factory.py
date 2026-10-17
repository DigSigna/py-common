import pytest

from py_common.audit.entities import AuditStrategy
from py_common.audit.factory import new_audit_recorder
from py_common.audit.hybrid_processor import HybridProcessor
from py_common.audit.ports import AuditStorage


class _FakeStorage(AuditStorage):
    def store_audit_record(self, record):
        pass


def test_database_strategy_builds_database_recorder():
    recorder = new_audit_recorder(
        AuditStrategy.DATABASE, _FakeStorage(), http_base_url=None, service_name="x"
    )
    assert recorder.__class__.__name__ == "_DatabaseRecorder"


def test_hybrid_without_http_base_url_downgrades_to_database():
    recorder = new_audit_recorder(
        AuditStrategy.HYBRID, _FakeStorage(), http_base_url="", service_name="x"
    )
    assert recorder.__class__.__name__ == "_DatabaseRecorder"


def test_hybrid_with_mock_url_downgrades_to_database():
    recorder = new_audit_recorder(
        AuditStrategy.HYBRID, _FakeStorage(), http_base_url="mock", service_name="x"
    )
    assert recorder.__class__.__name__ == "_DatabaseRecorder"


def test_hybrid_with_real_url_builds_hybrid_processor():
    recorder = new_audit_recorder(
        AuditStrategy.HYBRID,
        _FakeStorage(),
        http_base_url="https://audit.internal",
        service_name="certificate-service",
    )
    assert isinstance(recorder, HybridProcessor)
    assert recorder.primary is not None
    assert recorder.primary.session.headers["User-Agent"] == ("certificate-service/1.0")


@pytest.mark.asyncio
async def test_mock_strategy_is_a_true_noop():
    recorder = new_audit_recorder(
        AuditStrategy.MOCK, _FakeStorage(), http_base_url=None, service_name="x"
    )
    assert await recorder.record_event(None, "event-1") is None
