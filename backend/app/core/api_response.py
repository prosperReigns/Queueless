"""Standardized API response payload helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional


def success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
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
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
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
