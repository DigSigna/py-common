import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from py_common.auth.identity_context import IdentityContext
from py_common.auth.jwt_key_provider import JWTKeyProvider
from py_common.auth.owner_type import OwnerType
from py_common.auth.validator_adapter import JWTValidatorAdapter


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


class _FixedKeyProvider(JWTKeyProvider):
    def __init__(self, public_key):
        self._public_key = public_key

    def get_public_key(self, kid):
        return self._public_key


class _FakeTokenCache:
    def __init__(self, known_ids=None, raises=False):
        self._known_ids = known_ids or set()
        self._raises = raises

    def exists(self, token_id: str) -> bool:
        if self._raises:
            raise RuntimeError("redis unavailable")
        return token_id in self._known_ids


def _make_token(private_key, **extra_claims) -> str:
    claims = {"tenant_id": "tenant-1", "owner_id": "owner-1", **extra_claims}
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_validate_token_returns_claims(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(
        private_key,
        owner_type="USER",
        user_id="user-1",
        cert_level=2,
        max_cert_level=3,
        can_certify=True,
        certification_path="root/int",
        permissions=["admin"],
    )

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key), issuer=None, audience=None
    )
    claims = validator.validate_token(token)

    assert claims.tenant_id == "tenant-1"
    assert claims.owner_id == "owner-1"
    assert claims.cert_level == 2
    assert claims.can_certify is True
    assert claims.permissions == ["admin"]


# KD-015 (platform-docs/security/known-deviations.md): the real JWT
# identification-service issues encodes `permissions` as a flat JSON array,
# not a dict -- a bug previously went undetected because no test routed a
# genuinely signed token through validate_token() and on into
# IdentityContext.has_permission(). This exercises that exact real path:
# sign -> validate_token() -> build IdentityContext the same way
# AuthMiddleware.dispatch does -> has_permission(), with no hand-built
# IdentityContext shortcut anywhere in the chain.
def test_signed_token_permissions_array_flows_through_to_has_permission(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(
        private_key,
        owner_type="TENANT",
        user_id="",
        cert_level=0,
        max_cert_level=2,
        can_certify=True,
        certification_path="",
        permissions=["ca:bootstrap-self"],
    )

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key), issuer=None, audience=None
    )
    claims = validator.validate_token(token)

    identity = IdentityContext(
        tenant_id=claims.tenant_id,
        owner_type=OwnerType(claims.owner_type),
        owner_id=claims.owner_id,
        user_id=claims.user_id,
        cert_level=claims.cert_level,
        max_cert_level=claims.max_cert_level,
        can_certify=claims.can_certify,
        certification_path=claims.certification_path,
        permissions=claims.permissions,
        organization_id=claims.organization_id,
        parent_key_id=claims.parent_key_id,
    )

    assert identity.has_permission("ca:bootstrap-self") is True
    assert identity.has_permission("admin") is False


def test_validate_token_requires_tenant_id(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = jwt.encode({"owner_id": "owner-1"}, private_key, algorithm="RS256")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key), issuer=None, audience=None
    )

    with pytest.raises(ValueError, match="tenant_id is required"):
        validator.validate_token(token)


def test_validate_token_requires_owner_id(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = jwt.encode({"tenant_id": "tenant-1"}, private_key, algorithm="RS256")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key), issuer=None, audience=None
    )

    with pytest.raises(ValueError, match="owner_id is required"):
        validator.validate_token(token)


def test_token_cache_enabled_rejects_unknown_token(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(private_key, jti="token-1")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key),
        issuer=None,
        audience=None,
        token_cache=_FakeTokenCache(known_ids=set()),
        token_cache_enabled=True,
    )

    with pytest.raises(ValueError, match="token revoked or not found"):
        validator.validate_token(token)


def test_token_cache_enabled_accepts_known_token(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(private_key, jti="token-1")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key),
        issuer=None,
        audience=None,
        token_cache=_FakeTokenCache(known_ids={"token-1"}),
        token_cache_enabled=True,
    )

    claims = validator.validate_token(token)
    assert claims.token_id == "token-1"


def test_token_cache_non_strict_swallows_cache_errors(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(private_key, jti="token-1")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key),
        issuer=None,
        audience=None,
        token_cache=_FakeTokenCache(raises=True),
        token_cache_enabled=True,
        token_cache_strict=False,
    )

    # Does not raise despite the cache backend failing.
    validator.validate_token(token)


def test_token_cache_strict_propagates_cache_errors(rsa_keypair):
    private_key, public_key = rsa_keypair
    token = _make_token(private_key, jti="token-1")

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key),
        issuer=None,
        audience=None,
        token_cache=_FakeTokenCache(raises=True),
        token_cache_enabled=True,
        token_cache_strict=True,
    )

    with pytest.raises(RuntimeError, match="redis unavailable"):
        validator.validate_token(token)
