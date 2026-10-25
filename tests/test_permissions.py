from unittest.mock import MagicMock

import pytest

from py_common.auth.identity_context import IdentityContext
from py_common.auth.owner_type import OwnerType
from py_common.auth.permissions import require_admin
from py_common.errors import AuthorizationError


def _identity(permissions=None) -> IdentityContext:
    return IdentityContext(
        tenant_id="tenant-1",
        owner_type=OwnerType.TENANT,
        owner_id="owner-1",
        user_id="user-1",
        cert_level=0,
        max_cert_level=0,
        can_certify=False,
        certification_path="",
        permissions=permissions or [],
    )


def _request_with(identity: IdentityContext) -> MagicMock:
    request = MagicMock()
    request.state.identity_context = identity
    return request


def test_require_admin_passes_with_admin_permission():
    request = _request_with(_identity(["admin"]))

    result = require_admin(request)

    assert result.tenant_id == "tenant-1"


def test_require_admin_rejects_without_permissions():
    request = _request_with(_identity([]))

    with pytest.raises(AuthorizationError):
        require_admin(request)


def test_require_admin_rejects_with_other_permissions_only():
    request = _request_with(_identity(["hsm:key:generate", "certificate:revoke"]))

    with pytest.raises(AuthorizationError):
        require_admin(request)
