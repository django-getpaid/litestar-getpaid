"""Example Litestar application demonstrating litestar-getpaid.

This app provides:
- A simple order management UI (create orders, view order details)
- Payment processing via litestar-getpaid with multiple backends
  (Dummy, PayU, Paynow)
- A fake payment gateway simulator (paywall) for interactive testing
- Environment variable configuration for sandbox credentials

Payment flow:
1. User creates an order on the home page
2. User clicks "Pay" on the order detail page
3. The app calls the litestar-getpaid REST API to create a payment
4. The app registers the payment with the fake gateway (paywall)
5. User is redirected to the paywall authorization page
6. User approves or rejects the payment
7. The paywall sends a callback to the litestar-getpaid callback endpoint
8. The payment status is updated via the FSM
9. User is redirected back to the order detail page
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Annotated

import httpx
from getpaid_core.backends.dummy import DummyProcessor
from getpaid_core.registry import registry as global_registry
from litestar import Litestar, Request, Router, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template
from litestar.template import TemplateConfig
from models import Order as OrderModel
from paywall import configure as configure_paywall
from paywall import paywall_router
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.contrib.sqlalchemy.models import Base
from litestar_getpaid.contrib.sqlalchemy.repository import (
    SQLAlchemyPaymentRepository,
)
from litestar_getpaid.contrib.sqlalchemy.retry_store import (
    SQLAlchemyRetryStore,
)
from litestar_getpaid.plugin import create_payment_router

# --- Database setup ---

engine = create_async_engine(
    "sqlite+aiosqlite:///example.db",
    echo=True,
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)

# --- Order resolver ---


class ExampleOrderResolver:
    """Resolves order IDs to Order model instances from the database."""

    async def resolve(self, order_id: str) -> OrderModel:
        async with session_factory() as session:
            order = await session.get(OrderModel, order_id)
            if order is None:
                raise KeyError(f"Order {order_id} not found")
            session.expunge(order)
            return order


# --- Configuration ---

config = GetpaidConfig(
    default_backend=os.environ.get("GETPAID_DEFAULT_BACKEND", "dummy"),
    success_url="http://127.0.0.1:8001/order-success",
    failure_url="http://127.0.0.1:8001/order-failure",
    backends={
        "dummy": {
            "module": "getpaid_core.backends.dummy",
            "gateway": "http://127.0.0.1:8001/paywall/gateway",
            "confirmation_method": "push",
        },
        "payu": {
            "module": "getpaid_payu",
            "pos_id": os.environ.get("PAYU_POS_ID", "300746"),
            "second_key": os.environ.get(
                "PAYU_SECOND_KEY", "b6ca15b0d1020e8094d9b5f8d163db54"
            ),
            "oauth_id": os.environ.get("PAYU_OAUTH_ID", "300746"),
            "oauth_secret": os.environ.get(
                "PAYU_OAUTH_SECRET", "2ee86a66e5d97e3fadc400c9f19b065d"
            ),
            "sandbox": True,
        },
        "paynow": {
            "module": "getpaid_paynow",
            "api_key": os.environ.get(
                "PAYNOW_API_KEY", "d2e1d881-40b0-4b7e-9168-181bae3dc4e0"
            ),
            "signature_key": os.environ.get(
                "PAYNOW_SIGNATURE_KEY", "8e42a868-5562-440d-817c-4921632fb049"
            ),
            "sandbox": True,
        },
    },
)

# --- Payment router ---

repository = SQLAlchemyPaymentRepository(session_factory)
retry_store = SQLAlchemyRetryStore(session_factory)

# Manually register the dummy backend since it is not installed
# as a separate package with entry_points.
global_registry.register(DummyProcessor)

payment_router = create_payment_router(
    config=config,
    repository=repository,
    order_resolver=ExampleOrderResolver(),
    retry_store=retry_store,
)


# --- App lifespan ---


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    configure_paywall(session_factory)
    yield


# --- Order management views ---


@get("/")
async def home() -> Template:
    """Home page: list orders and create new ones."""
    async with session_factory() as session:
        result = await session.execute(
            select(OrderModel).order_by(OrderModel.created_at.desc())
        )
        orders = list(result.scalars().all())
        for o in orders:
            session.expunge(o)

    return Template(
        template_name="home.html",
        context={"orders": orders},
    )


@dataclass
class CreateOrderForm:
    """Form data for creating an order."""

    description: str
    amount: str
    currency: str = "PLN"


@post("/orders/create")
async def create_order(
    data: Annotated[
        CreateOrderForm,
        Body(media_type=RequestEncodingType.URL_ENCODED),
    ],
) -> Redirect | Template:
    """Create a new order and redirect to its detail page."""
    try:
        amount = Decimal(data.amount)
    except InvalidOperation:
        return Template(
            template_name="404.html",
            context={"message": "Invalid amount"},
            status_code=400,
        )
    if amount <= 0 or not amount.is_finite():
        return Template(
            template_name="404.html",
            context={"message": "Amount must be a positive number"},
            status_code=400,
        )
    async with session_factory() as session:
        order = OrderModel(
            description=data.description,
            amount=amount,
            currency=data.currency,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        order_id = order.id

    return Redirect(path=f"/orders/{order_id}", status_code=303)


@get("/orders/{order_id:str}")
async def order_detail(order_id: str) -> Template:
    """Order detail page: show order info and its payments."""
    async with session_factory() as session:
        order = await session.get(OrderModel, order_id)
        if order is None:
            return Template(
                template_name="404.html",
                context={"message": "Order not found"},
                status_code=404,
            )
        session.expunge(order)

    # Fetch payments for this order via the repository.
    payments = await repository.list_by_order(order_id)

    return Template(
        template_name="order_detail.html",
        context={"order": order, "payments": payments},
    )


@post("/orders/{order_id:str}/pay")
async def initiate_payment(
    request: Request,
    order_id: str,
) -> Redirect | Template:
    """Initiate a payment for an order.

    1. Call POST /api/payments/ to create a payment and run the
       payment flow (create + prepare via the backend).
    2. Register the payment with the fake gateway (paywall) and
       redirect the user there.
    """
    async with session_factory() as session:
        order = await session.get(OrderModel, order_id)
        if order is None:
            return Template(
                template_name="404.html",
                context={"message": "Order not found"},
                status_code=404,
            )
        session.expunge(order)

    base_url = str(request.base_url).rstrip("/")
    backend = os.environ.get("GETPAID_DEFAULT_BACKEND", "dummy")

    try:
        async with httpx.AsyncClient(base_url=base_url) as client:
            resp = await client.post(
                "/api/payments/",
                json={
                    "order_id": order_id,
                    "backend": backend,
                    "amount": str(order.amount),
                    "currency": order.currency,
                    "description": order.description,
                },
            )
            if resp.status_code != 201:
                error_detail = "Failed to create payment"
                try:
                    error_data = resp.json()
                    if "detail" in error_data:
                        error_detail = error_data["detail"]
                except Exception:
                    pass
                return Template(
                    template_name="404.html",
                    context={"message": f"Payment error: {error_detail}"},
                    status_code=400,
                )
            payment_data = resp.json()
    except httpx.RequestError as exc:
        return Template(
            template_name="404.html",
            context={"message": f"Network error: {exc}"},
            status_code=500,
        )

    payment_id = payment_data["payment_id"]

    callback_url = f"{base_url}/api/callback/{payment_id}"

    try:
        async with httpx.AsyncClient(base_url=base_url) as client:
            resp = await client.post(
                "/paywall/register",
                json={
                    "ext_id": payment_id,
                    "value": str(order.amount),
                    "currency": order.currency,
                    "description": order.description,
                    "callback": callback_url,
                    "success_url": f"{base_url}/orders/{order_id}",
                    "failure_url": f"{base_url}/orders/{order_id}",
                },
            )
            if resp.status_code != 200:
                return Template(
                    template_name="404.html",
                    context={
                        "message": "Failed to register with payment gateway"
                    },
                    status_code=400,
                )
            gateway_data = resp.json()
    except httpx.RequestError as exc:
        return Template(
            template_name="404.html",
            context={"message": f"Gateway connection error: {exc}"},
            status_code=500,
        )

    return Redirect(path=gateway_data["url"], status_code=303)


@get("/order-success")
async def order_success(payment_id: str = "") -> Template:
    """Success landing page after payment."""
    return Template(
        template_name="result.html",
        context={"status": "success", "payment_id": payment_id},
    )


@get("/order-failure")
async def order_failure(payment_id: str = "") -> Template:
    """Failure landing page after payment."""
    return Template(
        template_name="result.html",
        context={"status": "failure", "payment_id": payment_id},
    )


# --- App ---

api_router = Router(
    path="/api",
    route_handlers=[payment_router],
)

app = Litestar(
    route_handlers=[
        home,
        create_order,
        order_detail,
        initiate_payment,
        order_success,
        order_failure,
        api_router,
        paywall_router,
    ],
    lifespan=[lifespan],
    template_config=TemplateConfig(
        directory="templates",
        engine=JinjaTemplateEngine,
    ),
)
