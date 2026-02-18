"""Tests for the public API surface."""


def test_version():
    """Package exposes version."""
    from litestar_getpaid import __version__

    assert __version__ == "0.1.1"


def test_create_payment_router_importable():
    """Main factory function is importable from package root."""
    from litestar_getpaid import create_payment_router

    assert callable(create_payment_router)


def test_config_importable():
    """Config class is importable from package root."""
    from litestar_getpaid import GetpaidConfig

    assert GetpaidConfig is not None


def test_schemas_importable():
    """Key schemas are importable from package root."""
    from litestar_getpaid import (
        CallbackRetryResponse,
        CreatePaymentRequest,
        CreatePaymentResponse,
        ErrorResponse,
        PaymentListResponse,
        PaymentResponse,
    )

    assert all(
        [
            CreatePaymentRequest,
            CreatePaymentResponse,
            PaymentResponse,
            PaymentListResponse,
            ErrorResponse,
            CallbackRetryResponse,
        ]
    )


def test_protocols_importable():
    """Protocols are importable from package root."""
    from litestar_getpaid import (
        CallbackRetryStore,
        OrderResolver,
        PaymentWithHelpers,
    )

    assert all([PaymentWithHelpers, OrderResolver, CallbackRetryStore])


def test_registry_importable():
    """Registry is importable from package root."""
    from litestar_getpaid import LitestarPluginRegistry

    assert LitestarPluginRegistry is not None


def test_exception_importable():
    """Custom exceptions are importable."""
    from litestar_getpaid import ConfigurationError, PaymentNotFoundError

    assert PaymentNotFoundError is not None
    assert ConfigurationError is not None
