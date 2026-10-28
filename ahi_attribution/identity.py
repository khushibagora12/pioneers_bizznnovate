import uuid

from flask import current_app, request

COOKIE_NAME = "ahi_visitor"


def get_or_create_visitor_id() -> tuple[str, bool]:
    """Return (visitor UUID, whether it is newly created)."""
    value = request.cookies.get(COOKIE_NAME, "")
    try:
        return str(uuid.UUID(value)), False
    except (ValueError, TypeError, AttributeError):
        return str(uuid.uuid4()), True


def attach_visitor_cookie(response, visitor_id: str):
    response.set_cookie(
        COOKIE_NAME,
        visitor_id,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite="Lax",
        path="/",
    )
    return response
