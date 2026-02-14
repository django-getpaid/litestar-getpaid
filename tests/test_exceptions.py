"""Tests for exception-to-HTTP-response mapping."""

from litestar import Litestar, get
from litestar.testing import TestClient

from litestar_getpaid.exceptions import EXCEPTION_HANDLERS


def test_getpaid_exception_returns_400():
    """GetPaidException maps to 400."""
    from getpaid_core.exceptions import GetPaidException

    @get("/test")
    async def handler() -> None:
        raise GetPaidException("bad request")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"] == "bad request"
        assert data["code"] == "payment_error"


def test_communication_error_returns_502():
    """CommunicationError maps to 502."""
    from getpaid_core.exceptions import CommunicationError

    @get("/test")
    async def handler() -> None:
        raise CommunicationError("gateway down")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 502
        assert resp.json()["code"] == "communication_error"


def test_invalid_callback_returns_400():
    """InvalidCallbackError maps to 400."""
    from getpaid_core.exceptions import InvalidCallbackError

    @get("/test")
    async def handler() -> None:
        raise InvalidCallbackError("bad signature")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_callback"


def test_invalid_transition_returns_409():
    """InvalidTransitionError maps to 409."""
    from getpaid_core.exceptions import InvalidTransitionError

    @get("/test")
    async def handler() -> None:
        raise InvalidTransitionError("wrong state")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "invalid_transition"


def test_credentials_error_returns_500():
    """CredentialsError maps to 500."""
    from getpaid_core.exceptions import CredentialsError

    @get("/test")
    async def handler() -> None:
        raise CredentialsError("missing API key")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 500
        assert resp.json()["code"] == "credentials_error"


def test_charge_failure_returns_502():
    """ChargeFailure (subclass of CommunicationError) maps to 502."""
    from getpaid_core.exceptions import ChargeFailure

    @get("/test")
    async def handler() -> None:
        raise ChargeFailure("charge failed")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 502
        assert resp.json()["code"] == "communication_error"


def test_payment_not_found_returns_404():
    """PaymentNotFoundError maps to 404."""
    from litestar_getpaid.exceptions import PaymentNotFoundError

    @get("/test")
    async def handler() -> None:
        raise PaymentNotFoundError("pay-123")

    app = Litestar(
        route_handlers=[handler],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    with TestClient(app) as client:
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"
