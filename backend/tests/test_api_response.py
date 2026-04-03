"""Tests for standard API response helpers."""

from app.core.api_response import error_response, success_response


def test_success_response_shape() -> None:
    payload = success_response(data={"status": "ok"}, message="healthy")

    assert payload == {
        "success": True,
        "message": "healthy",
        "data": {"status": "ok"},
    }


def test_error_response_shape() -> None:
    payload = error_response(
        error="Too many requests.",
        code="RATE_LIMIT_EXCEEDED",
        details=None,
        request_id="req-123",
    )

    assert payload == {
        "success": False,
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests.",
            "details": None,
        },
        "request_id": "req-123",
    }


def test_error_response_includes_request_id_key_when_missing() -> None:
    payload = error_response(
        error="Internal server error.",
        code="INTERNAL_SERVER_ERROR",
    )

    assert "request_id" in payload
    assert payload["request_id"] is None
