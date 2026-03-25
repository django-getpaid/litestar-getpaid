"""Tests for payment CRUD routes (Litestar controllers)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from getpaid_core.types import TransactionResult
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import EXCEPTION_HANDLERS
from litestar_getpaid.registry import LitestarPluginRegistry
from litestar_getpaid.routes.payments import PaymentController


class DummyOrder:
    def __init__(self, order_id: str = "order-1") -> None:
        self.id = order_id
        self.description = "Test order"
        self.currency = "PLN"
        self.total = Decimal("100")

    def get_total_amount(self) -> Decimal:
        return self.total

    def get_buyer_info(self) -> dict:
        return {"email": "test@example.com"}

    def get_description(self) -> str:
        return self.description

    def get_currency(self) -> str:
        return self.currency

    def get_items(self) -> list[dict]:
        return []

    def get_return_url(self, success: bool | None = None) -> str:
        return "/return"


class DummyRegistry(LitestarPluginRegistry):
    _discovered = True

    def discover(self) -> None:
        self._discovered = True


@pytest.fixture
def config():
    return GetpaidConfig(
        default_backend="dummy",
        success_url="/ok",
        failure_url="/fail",
        backends={"dummy": {"sandbox": True}},
    )


@pytest.fixture
def mock_payment():
    payment = AsyncMock()
    payment.id = "pay-1"
    payment.order = DummyOrder()
    payment.order_id = "order-1"
    payment.amount_required = Decimal("100")
    payment.currency = "PLN"
    payment.status = "new"
    payment.backend = "dummy"
    payment.external_id = None
    payment.description = "Test payment"
    payment.amount_paid = Decimal("0")
    payment.amount_locked = Decimal("0")
    payment.amount_refunded = Decimal("0")
    payment.fraud_status = None
    payment.fraud_message = None
    payment.provider_data = {"customer_ip": "127.0.0.1"}
    return payment


@pytest.fixture
def mock_repo(mock_payment):
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=mock_payment)
    repo.list_by_order = AsyncMock(return_value=[mock_payment])
    repo.create = AsyncMock(return_value=mock_payment)
    repo.save = AsyncMock(return_value=mock_payment)
    return repo


@pytest.fixture
def app(config, mock_repo):
    return Litestar(
        route_handlers=[PaymentController],
        dependencies={
            "config": Provide(lambda: config, sync_to_thread=False),
            "repository": Provide(lambda: mock_repo, sync_to_thread=False),
            "registry": Provide(
                lambda: DummyRegistry(),
                sync_to_thread=False,
            ),
            "order_resolver": Provide(lambda: None, sync_to_thread=False),
        },
        exception_handlers=EXCEPTION_HANDLERS,
    )


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def test_get_payment(client, mock_payment):
    """GET /payments/{id} returns payment data."""
    resp = client.get("/payments/pay-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "pay-1"
    assert data["status"] == "new"


def test_get_payment_not_found(client, mock_repo):
    """GET /payments/{id} returns 404 for unknown payment."""
    mock_repo.get_by_id = AsyncMock(side_effect=KeyError("pay-999"))
    resp = client.get("/payments/pay-999")
    assert resp.status_code == 404


def test_list_payments(client, mock_repo, mock_payment):
    """GET /payments/ returns list of payments."""
    mock_repo.list_by_order = AsyncMock(return_value=[mock_payment])
    resp = client.get("/payments/?order_id=order-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_create_payment(config, mock_repo, mock_payment):
    """POST /payments/ creates a new payment."""
    mock_order = DummyOrder()

    resolver = AsyncMock()
    resolver.resolve = AsyncMock(return_value=mock_order)

    app = Litestar(
        route_handlers=[PaymentController],
        dependencies={
            "config": Provide(lambda: config, sync_to_thread=False),
            "repository": Provide(lambda: mock_repo, sync_to_thread=False),
            "registry": Provide(
                lambda: DummyRegistry(),
                sync_to_thread=False,
            ),
            "order_resolver": Provide(lambda: resolver, sync_to_thread=False),
        },
        exception_handlers=EXCEPTION_HANDLERS,
    )

    with patch("litestar_getpaid.routes.payments.PaymentFlow") as mock_flow_cls:
        instance = AsyncMock()
        mock_flow_cls.return_value = instance
        instance.create_payment = AsyncMock(return_value=mock_payment)
        instance.prepare = AsyncMock(
            return_value=TransactionResult(
                redirect_url="https://gateway.example.com/pay",
                form_data=None,
                method="GET",
                external_id="ext-123",
                provider_data={"customer_ip": "127.0.0.1"},
            )
        )

        with TestClient(app) as test_client:
            resp = test_client.post(
                "/payments/",
                json={
                    "order_id": "order-1",
                    "backend": "dummy",
                },
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_id"] == "pay-1"
    assert data["redirect_url"] == "https://gateway.example.com/pay"
    assert data["provider_data"] == {"customer_ip": "127.0.0.1"}


def test_payment_response_includes_provider_data(client):
    resp = client.get("/payments/pay-1")
    assert resp.status_code == 200
    assert resp.json()["provider_data"] == {"customer_ip": "127.0.0.1"}


def test_create_payment_without_resolver(app):
    """POST /payments/ returns 500 when no order resolver configured."""
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/payments/",
            json={
                "order_id": "order-1",
                "backend": "dummy",
            },
        )
    assert resp.status_code == 500
    data = resp.json()
    assert data["code"] == "configuration_error"


def test_list_payments_missing_order_id(client):
    """GET /payments/ without order_id query param returns 400."""
    resp = client.get("/payments/")
    assert resp.status_code == 400
