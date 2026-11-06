import pytest
from starlette.requests import Request
from starlette.responses import Response

from py_common.core.request_context import request_id_var
from py_common.middleware.request_context import RequestContextMiddleware


def _make_request(headers: dict) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/echo",
        "query_string": b"",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


async def _call_next(_request: Request) -> Response:
    return Response(content=request_id_var.get(), status_code=200)


@pytest.mark.asyncio
async def test_idempotency_key_header_is_used_as_request_id():
    middleware = RequestContextMiddleware(app=None)
    request = _make_request({"Idempotency-Key": "claim-123"})

    response = await middleware.dispatch(request, _call_next)

    assert response.body.decode() == "claim-123"
    assert response.headers["idempotency-key"] == "claim-123"


@pytest.mark.asyncio
async def test_legacy_x_request_id_header_no_longer_claims_idempotency():
    middleware = RequestContextMiddleware(app=None)
    request = _make_request({"X-Request-ID": "legacy-456"})

    response = await middleware.dispatch(request, _call_next)

    assert response.body.decode() != "legacy-456"
    assert "x-request-id" not in response.headers


@pytest.mark.asyncio
async def test_missing_header_generates_a_request_id():
    middleware = RequestContextMiddleware(app=None)
    request = _make_request({})

    response = await middleware.dispatch(request, _call_next)

    assert response.body.decode()
    assert "idempotency-key" in response.headers
