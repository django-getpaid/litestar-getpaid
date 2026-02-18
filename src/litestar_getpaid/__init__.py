"""Litestar framework adapter for getpaid payment processing."""

from typing import TYPE_CHECKING

__version__ = "3.0.0a2"

__all__ = [
    "CallbackRetryResponse",
    "CallbackRetryStore",
    "ConfigurationError",
    "CreatePaymentRequest",
    "CreatePaymentResponse",
    "ErrorResponse",
    "GetpaidConfig",
    "LitestarPluginRegistry",
    "OrderResolver",
    "PaymentListResponse",
    "PaymentNotFoundError",
    "PaymentResponse",
    "PaymentWithHelpers",
    "__version__",
    "create_payment_router",
]

if TYPE_CHECKING:
    from litestar_getpaid.config import GetpaidConfig
    from litestar_getpaid.exceptions import (
        ConfigurationError,
        PaymentNotFoundError,
    )
    from litestar_getpaid.plugin import create_payment_router
    from litestar_getpaid.protocols import (
        CallbackRetryStore,
        OrderResolver,
        PaymentWithHelpers,
    )
    from litestar_getpaid.registry import LitestarPluginRegistry
    from litestar_getpaid.schemas import (
        CallbackRetryResponse,
        CreatePaymentRequest,
        CreatePaymentResponse,
        ErrorResponse,
        PaymentListResponse,
        PaymentResponse,
    )


def __getattr__(name: str):
    # Lazy imports to avoid loading all submodules on package import.
    if name == "GetpaidConfig":
        from litestar_getpaid.config import GetpaidConfig

        return GetpaidConfig
    if name == "create_payment_router":
        from litestar_getpaid.plugin import create_payment_router

        return create_payment_router
    if name == "LitestarPluginRegistry":
        from litestar_getpaid.registry import LitestarPluginRegistry

        return LitestarPluginRegistry
    if name == "PaymentNotFoundError":
        from litestar_getpaid.exceptions import PaymentNotFoundError

        return PaymentNotFoundError
    if name == "ConfigurationError":
        from litestar_getpaid.exceptions import ConfigurationError

        return ConfigurationError
    if name in (
        "PaymentWithHelpers",
        "OrderResolver",
        "CallbackRetryStore",
    ):
        from litestar_getpaid import protocols

        return getattr(protocols, name)
    if name in (
        "CreatePaymentRequest",
        "CreatePaymentResponse",
        "PaymentResponse",
        "PaymentListResponse",
        "ErrorResponse",
        "CallbackRetryResponse",
    ):
        from litestar_getpaid import schemas

        return getattr(schemas, name)
    raise AttributeError(f"module 'litestar_getpaid' has no attribute {name!r}")
