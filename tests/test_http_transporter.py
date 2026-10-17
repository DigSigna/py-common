from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from py_common.audit.http_transporter import HttpAuditTransporter

_FAKE_EVENT = SimpleNamespace(event_type="TEST")


def test_user_agent_includes_service_name():
    transporter = HttpAuditTransporter("https://audit.internal", "signing-service")
    assert transporter.session.headers["User-Agent"] == "signing-service/1.0"


def test_send_posts_to_events_endpoint():
    transporter = HttpAuditTransporter("https://audit.internal/", "certificate-service")
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with patch.object(
        transporter.session, "post", return_value=fake_response
    ) as post_mock:
        transporter.send(None, event=_FAKE_EVENT)

    args, kwargs = post_mock.call_args
    assert args[0] == "https://audit.internal/api/v1/events"


def test_send_raises_runtime_error_on_request_failure():
    transporter = HttpAuditTransporter("https://audit.internal", "certificate-service")

    with patch.object(
        transporter.session,
        "post",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(RuntimeError, match="Error enviando evento"):
            transporter.send(None, event=_FAKE_EVENT)


def test_health_check_raises_runtime_error_on_failure():
    transporter = HttpAuditTransporter("https://audit.internal", "certificate-service")

    with patch.object(
        transporter.session,
        "get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(RuntimeError, match="Error en health check"):
            transporter.health_check(None)
