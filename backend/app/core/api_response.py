"""Standardized API response payload helpers."""

from __future__ import annotations

from typing import Any


def success_response(data: Any = None, message: str = "success") -> dict[str, Any]:
    """Build a standard success API payload."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(
    *,
    error: str,
    code: str,
    details: Any = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a standard error API payload."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": error,
            "details": details,
        },
        "request_id": request_id,
    }
