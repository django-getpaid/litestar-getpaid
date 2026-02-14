"""Tests for success/failure redirect endpoints."""

from unittest.mock import AsyncMock

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import EXCEPTION_HANDLERS
from litestar_getpaid.routes.redirects import RedirectController


@pytest.fixture
def config():
    return GetpaidConfig(
        default_backend="dummy",
        success_url="https://shop.example.com/thank-you",
        failure_url="https://shop.example.com/payment-failed",
        backends={},
    )


@pytest.fixture
def mock_payment():
    payment = AsyncMock()
    payment.id = "pay-1"
    payment.status = "paid"
    payment.backend = "dummy"
    return payment


@pytest.fixture
def mock_repo(mock_payment):
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=mock_payment)
    return repo


@pytest.fixture
def app(config, mock_repo):
    return Litestar(
        route_handlers=[RedirectController],
        dependencies={
            "config": Provide(lambda: config, sync_to_thread=False),
            "repository": Provide(lambda: mock_repo, sync_to_thread=False),
        },
        exception_handlers=EXCEPTION_HANDLERS,
    )


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        client.follow_redirects = False
        yield client


def test_success_redirect(client):
    """GET /success/{id} redirects to success_url."""
    resp = client.get("/success/pay-1")
    assert resp.status_code in (301, 302, 303, 307)
    assert "thank-you" in resp.headers["location"]


def test_failure_redirect(client):
    """GET /failure/{id} redirects to failure_url."""
    resp = client.get("/failure/pay-1")
    assert resp.status_code in (301, 302, 303, 307)
    assert "payment-failed" in resp.headers["location"]


def test_success_payment_not_found(client, mock_repo):
    """GET /success/{id} returns 404 for unknown payment."""
    mock_repo.get_by_id = AsyncMock(side_effect=KeyError("pay-999"))
    resp = client.get("/success/pay-999")
    assert resp.status_code == 404


def test_failure_payment_not_found(client, mock_repo):
    """GET /failure/{id} returns 404 for unknown payment."""
    mock_repo.get_by_id = AsyncMock(side_effect=KeyError("pay-999"))
    resp = client.get("/failure/pay-999")
    assert resp.status_code == 404
