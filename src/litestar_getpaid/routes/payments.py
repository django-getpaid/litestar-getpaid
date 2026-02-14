"""Payment CRUD routes."""

import logging
from typing import Annotated, Any

from getpaid_core.flow import PaymentFlow
from getpaid_core.protocols import PaymentRepository
from litestar import Controller, get, post
from litestar.params import Dependency

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import ConfigurationError, PaymentNotFoundError
from litestar_getpaid.protocols import OrderResolver
from litestar_getpaid.schemas import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentListResponse,
    PaymentResponse,
)

logger = logging.getLogger(__name__)


def _payment_to_response(payment: Any) -> PaymentResponse:
    """Convert a Payment protocol object to PaymentResponse."""
    order_id = getattr(payment, "order_id", None)
    if order_id is None:
        order = getattr(payment, "order", None)
        order_id = str(getattr(order, "id", "")) if order is not None else ""
    return PaymentResponse(
        id=str(payment.id),
        order_id=str(order_id),
        amount_required=payment.amount_required,
        currency=payment.currency,
        status=payment.status,
        backend=payment.backend,
        description=payment.description,
        external_id=payment.external_id,
        amount_paid=payment.amount_paid,
        amount_locked=payment.amount_locked,
        amount_refunded=payment.amount_refunded,
        fraud_status=payment.fraud_status,
        fraud_message=payment.fraud_message,
    )


class PaymentController(Controller):
    """Payment CRUD endpoints."""

    path = "/payments"
    tags = ["payments"]

    @get("/{payment_id:str}")
    async def get_payment(
        self,
        payment_id: str,
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
    ) -> PaymentResponse:
        """Get a single payment by ID."""
        try:
            payment = await repository.get_by_id(payment_id)
        except KeyError as exc:
            raise PaymentNotFoundError(payment_id) from exc
        return _payment_to_response(payment)

    @get("/")
    async def list_payments(
        self,
        order_id: str,
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
    ) -> PaymentListResponse:
        """List payments for an order."""
        payments = await repository.list_by_order(order_id)
        items = [_payment_to_response(p) for p in payments]
        return PaymentListResponse(items=items, total=len(items))

    @post("/", status_code=201)
    async def create_payment(
        self,
        data: CreatePaymentRequest,
        config: Annotated[GetpaidConfig, Dependency(skip_validation=True)],
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
        order_resolver: Annotated[
            OrderResolver | None, Dependency(skip_validation=True)
        ] = None,
    ) -> CreatePaymentResponse:
        """Create a new payment and prepare it for processing."""
        if order_resolver is None:
            raise ConfigurationError("No order resolver configured")
        order = await order_resolver.resolve(data.order_id)
        flow = PaymentFlow(repository=repository, config=config.backends)
        payment = await flow.create_payment(order, data.backend)
        result = await flow.prepare(payment)
        return CreatePaymentResponse(
            payment_id=str(payment.id),
            redirect_url=result.get("redirect_url"),
            method=result.get("method", "GET"),
            form_data=result.get("form_data"),
        )
