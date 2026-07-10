import logging

from fastapi.testclient import TestClient

from src.api.request_context import RequestIDLogFilter, request_id_var
from src.main import app


def _make_record() -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )


def test_request_id_log_filter_injects_current_value():
    token = request_id_var.set("abc-123")
    try:
        record = _make_record()
        RequestIDLogFilter().filter(record)
        assert record.request_id == "abc-123"
    finally:
        request_id_var.reset(token)


def test_request_id_log_filter_defaults_when_unset():
    record = _make_record()
    RequestIDLogFilter().filter(record)
    assert record.request_id == "-"


def test_response_includes_generated_request_id_header():
    client = TestClient(app)
    response = client.get("/health")

    assert len(response.headers["x-request-id"]) > 0


def test_response_echoes_incoming_request_id_header():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "caller-supplied-id"})

    assert response.headers["x-request-id"] == "caller-supplied-id"


def test_each_request_gets_a_distinct_generated_request_id():
    client = TestClient(app)
    first = client.get("/health")
    second = client.get("/health")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]
