import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from py_common.auth.jwt_key_provider import JWTKeyProvider
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
        permissions={"admin": True},
    )

    validator = JWTValidatorAdapter(
        key_manager=_FixedKeyProvider(public_key), issuer=None, audience=None
    )
    claims = validator.validate_token(token)

    assert claims.tenant_id == "tenant-1"
    assert claims.owner_id == "owner-1"
    assert claims.cert_level == 2
    assert claims.can_certify is True
    assert claims.permissions == {"admin": True}


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
