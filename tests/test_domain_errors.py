"""Unit tests for DomainError.to_dict().

Regression for a cross-cutting bug found while testing certificate-service's
verification feature: to_dict() only ever serialized the base message/
details, so every subclass's own extra field was silently dropped from the
HTTP error response. Only the generic base lives in py_common; each
consuming service keeps its own domain-specific subclasses (and their own
tests) in its own repo.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar, Optional

from py_common.errors import DuplicateRequestError, NotFoundError, ValidationError
from py_common.errors.base import DomainError


@dataclass
class _FakeLockedError(DomainError):
    """Local stand-in for a service's own datetime-carrying subclass (e.g.
    certificate-service's SigningPinLockedError.locked_until) — exercises
    the same to_dict() datetime-serialization path without depending on a
    domain-specific error that doesn't live in this package."""

    code: ClassVar[str] = "FAKE_LOCKED"
    http_status: ClassVar[int] = 423

    locked_until: Optional[datetime] = None


def test_to_dict_merges_subclass_field_with_manual_details():
    error = ValidationError(
        "bad input", details={"extra": "context"}, field="algorithm"
    )

    assert error.to_dict() == {
        "code": "VALIDATION_ERROR",
        "message": "bad input",
        "details": {"field": "algorithm", "extra": "context"},
    }


def test_to_dict_omits_unset_subclass_field():
    error = NotFoundError("not found")  # entity/entity_id left unset (None)

    assert error.to_dict() == {
        "code": "NOT_FOUND",
        "message": "not found",
        "details": {},
    }


def test_to_dict_with_only_base_fields_is_unaffected():
    error = DuplicateRequestError("duplicate", idempotency_key="abc")

    assert error.to_dict() == {
        "code": "DUPLICATE_REQUEST",
        "message": "duplicate",
        "details": {"idempotency_key": "abc"},
    }


def test_to_dict_serializes_datetime_fields():
    """datetime fields must come out as isoformat strings, not raw
    datetimes: JSONResponse.render() (ErrorHandlingMiddleware) calls plain
    json.dumps() with no custom default, which raises TypeError on a raw
    datetime."""
    locked_until = datetime(2026, 1, 1, tzinfo=timezone.utc)
    error = _FakeLockedError("locked", locked_until=locked_until)

    result = error.to_dict()
    assert result == {
        "code": "FAKE_LOCKED",
        "message": "locked",
        "details": {"locked_until": "2026-01-01T00:00:00+00:00"},
    }
    json.dumps(result)  # must not raise


def test_with_detail_returns_new_instance_without_mutating_original():
    error = ValidationError("bad input")

    updated = error.with_detail("field", "algorithm")

    assert error.details == {}
    assert updated.details == {"field": "algorithm"}


def test_get_error_code_for_domain_error():
    from py_common.errors import get_error_code

    assert get_error_code(ValidationError("bad input")) == "VALIDATION_ERROR"
    assert get_error_code(RuntimeError("boom")) == "INTERNAL_ERROR"
    assert get_error_code(None) == "SUCCESS"
