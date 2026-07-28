import json
import logging

from autobiz.logging import JsonFormatter


def test_json_formatter_emits_correlation_fields_without_message_args():
    record = logging.LogRecord(
        name="autobiz.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request.completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "request.completed"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 200
    assert "args" not in payload


def test_request_id_is_preserved_or_replaced(client):
    response = client.get("/health/", headers={"X-Request-ID": "safe-id-123"})
    unsafe_response = client.get("/health/", headers={"X-Request-ID": "unsafe id with spaces"})

    assert response.headers["X-Request-ID"] == "safe-id-123"
    assert unsafe_response.headers["X-Request-ID"] != "unsafe id with spaces"
    assert len(unsafe_response.headers["X-Request-ID"]) == 32
