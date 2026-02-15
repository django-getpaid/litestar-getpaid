"""Full-stack integration tests: router + real SQLAlchemy repo + retry store."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

from getpaid_core.exceptions import CommunicationError
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.contrib.sqlalchemy.models import CallbackRetryModel
from litestar_getpaid.contrib.sqlalchemy.repository import (
    SQLAlchemyPaymentRepository,
)
from litestar_getpaid.contrib.sqlalchemy.retry_store import (
    SQLAlchemyRetryStore,
)
from litestar_getpaid.plugin import create_payment_router


def _make_full_app(
    *,
    config: GetpaidConfig,
    repo: SQLAlchemyPaymentRepository,
    retry_store: SQLAlchemyRetryStore | None = None,
    order_resolver: object | None = None,
) -> Litestar:
    """Build a Litestar app with the full getpaid router."""
    router = create_payment_router(
        config=config,
        repository=repo,
        retry_store=retry_store,
        order_resolver=order_resolver,
    )
    return Litestar(route_handlers=[router])


def test_full_app_starts(
    getpaid_config: GetpaidConfig,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Full app with real repo + retry store starts and returns 404 for
    a nonexistent payment."""
    repo = SQLAlchemyPaymentRepository(
        session_factory=async_session_factory,
    )
    retry_store = SQLAlchemyRetryStore(
        session_factory=async_session_factory,
    )
    app = _make_full_app(
        config=getpaid_config,
        repo=repo,
        retry_store=retry_store,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/payments/nonexistent-id")

    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "not_found"
    assert "nonexistent-id" in data["detail"]


def test_create_and_get_payment(
    getpaid_config: GetpaidConfig,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """POST creates a payment (mocked flow), response has payment_id
    and redirect_url."""
    repo = SQLAlchemyPaymentRepository(
        session_factory=async_session_factory,
    )
    order_resolver = AsyncMock()
    order_resolver.resolve = AsyncMock(return_value=AsyncMock())

    app = _make_full_app(
        config=getpaid_config,
        repo=repo,
        order_resolver=order_resolver,
    )

    mock_payment = AsyncMock()
    mock_payment.id = "test-pay-1"
    mock_payment.order_id = "order-1"
    mock_payment.amount_required = Decimal("100.00")
    mock_payment.currency = "PLN"
    mock_payment.status = "new"
    mock_payment.backend = "dummy"
    mock_payment.external_id = None
    mock_payment.description = "Integration test"
    mock_payment.amount_paid = Decimal("0")
    mock_payment.amount_locked = Decimal("0")
    mock_payment.amount_refunded = Decimal("0")
    mock_payment.fraud_status = None
    mock_payment.fraud_message = None

    with patch(
        "litestar_getpaid.routes.payments.PaymentFlow",
    ) as mock_flow_cls:
        instance = AsyncMock()
        mock_flow_cls.return_value = instance
        instance.create_payment = AsyncMock(return_value=mock_payment)
        instance.prepare = AsyncMock(
            return_value={
                "redirect_url": "https://gateway.example.com/pay",
                "form_data": None,
                "method": "GET",
                "headers": {},
            }
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/payments/",
                json={
                    "order_id": "order-1",
                    "backend": "dummy",
                },
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_id"] == "test-pay-1"
    assert data["redirect_url"] == "https://gateway.example.com/pay"
    assert data["method"] == "GET"


async def test_callback_with_retry_on_failure(
    getpaid_config: GetpaidConfig,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Failed callback returns 502 with callback_failed code
    and stores a retry entry in the real retry store."""
    repo = SQLAlchemyPaymentRepository(
        session_factory=async_session_factory,
    )
    retry_store = SQLAlchemyRetryStore(
        session_factory=async_session_factory,
        backoff_seconds=5,
    )

    # Pre-populate a payment in the DB so the callback route can find it.
    payment = await repo.create(
        order_id="order-cb-1",
        amount_required=Decimal("50.00"),
        currency="PLN",
        backend="dummy",
        description="Callback test",
    )

    app = _make_full_app(
        config=getpaid_config,
        repo=repo,
        retry_store=retry_store,
    )

    with patch(
        "litestar_getpaid.routes.callbacks.PaymentFlow",
    ) as mock_flow_cls:
        instance = AsyncMock()
        mock_flow_cls.return_value = instance
        instance.handle_callback = AsyncMock(
            side_effect=CommunicationError("gateway timeout"),
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                f"/callback/{payment.id}",
                json={"status": "paid"},
            )

    assert resp.status_code == 502
    data = resp.json()
    assert data["code"] == "callback_failed"
    assert "gateway timeout" in data["detail"]

    # Verify the retry was persisted in the real DB by querying
    # the model table directly (get_due_retries filters by
    # next_retry_at <= now, but the backoff pushes it into the future).
    async with async_session_factory() as session:
        stmt = select(CallbackRetryModel).where(
            CallbackRetryModel.payment_id == payment.id,
        )
        result = await session.execute(stmt)
        retries = list(result.scalars().all())

    assert len(retries) == 1
    retry = retries[0]
    assert retry.payment_id == payment.id
    assert retry.payload["status"] == "paid"
    assert retry.payload["_raw_body"] == '{"status":"paid"}'
    assert retry.status == "pending"
    assert retry.attempts == 0


async def test_success_redirect(
    getpaid_config: GetpaidConfig,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """GET /success/{id} redirects to success_url with payment_id."""
    repo = SQLAlchemyPaymentRepository(
        session_factory=async_session_factory,
    )

    # Pre-populate a payment so the redirect route can find it.
    payment = await repo.create(
        order_id="order-redir-1",
        amount_required=Decimal("75.00"),
        currency="PLN",
        backend="dummy",
        description="Redirect test",
    )

    app = _make_full_app(
        config=getpaid_config,
        repo=repo,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        client.follow_redirects = False
        resp = client.get(f"/success/{payment.id}")

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location == f"/success?payment_id={payment.id}"
