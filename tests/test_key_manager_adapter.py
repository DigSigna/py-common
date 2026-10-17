from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from py_common.auth.key_manager_adapter import KeyManagerAdapter, KeyManagerConfig


def _write_public_key_pem(path, private_key) -> None:
    pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem)


@pytest.fixture
def rsa_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_development_mode_loads_pem_as_dev_key(tmp_path, rsa_private_key):
    pem_path = tmp_path / "public.pem"
    _write_public_key_pem(pem_path, rsa_private_key)

    manager = KeyManagerAdapter(
        KeyManagerConfig(mode="development", public_key_path=str(pem_path), jwks_url="")
    )

    # No kid (dev tokens aren't signed with a kid header) falls back to the
    # single loaded "dev-key".
    assert manager.get_public_key(None) is not None
    # An explicit, unknown kid is never silently matched to "dev-key".
    with pytest.raises(ValueError, match="public key not found for kid"):
        manager.get_public_key("whatever-kid")


def test_development_mode_without_key_path_raises():
    with pytest.raises(ValueError, match="AUTH_PUBLIC_KEY_PATH"):
        KeyManagerAdapter(
            KeyManagerConfig(mode="development", public_key_path="", jwks_url="")
        )


def test_production_mode_fetches_jwks_and_resolves_by_kid(rsa_private_key):
    jwk_payload = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "key-1",
                "n": "x",
                "e": "AQAB",
            }
        ]
    }
    fake_response = MagicMock()
    fake_response.json.return_value = jwk_payload
    fake_response.raise_for_status.return_value = None

    fake_public_key = object()

    with (
        patch(
            "py_common.auth.key_manager_adapter.requests.get",
            return_value=fake_response,
        ),
        patch(
            "py_common.auth.key_manager_adapter.RSAAlgorithm.from_jwk",
            return_value=fake_public_key,
        ),
    ):
        manager = KeyManagerAdapter(
            KeyManagerConfig(
                mode="production",
                public_key_path="",
                jwks_url="https://issuer.example/.well-known/jwks.json",
            )
        )

    assert manager.get_public_key("key-1") is fake_public_key
    with pytest.raises(ValueError, match="public key not found for kid"):
        manager.get_public_key("missing-kid")


def test_production_mode_without_jwks_url_raises():
    with pytest.raises(ValueError, match="JWKS URL not configured"):
        KeyManagerAdapter(
            KeyManagerConfig(mode="production", public_key_path="", jwks_url="")
        )
