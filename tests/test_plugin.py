"""Tests for the router factory function."""

from unittest.mock import AsyncMock

from litestar import Router

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import EXCEPTION_HANDLERS
from litestar_getpaid.plugin import create_payment_router
from litestar_getpaid.registry import LitestarPluginRegistry


def _make_config() -> GetpaidConfig:
    return GetpaidConfig(
        default_backend="dummy",
        success_url="/ok",
        failure_url="/fail",
        backends={"dummy": {}},
    )


def test_create_payment_router_returns_router() -> None:
    """Factory returns a Litestar Router."""
    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
    )
    assert isinstance(router, Router)


def test_create_payment_router_includes_all_route_groups() -> None:
    """Router includes payment, callback, and redirect routes."""
    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
    )

    paths = {route.path for route in router.routes}

    # PaymentController routes
    assert "/payments" in paths
    assert "/payments/{payment_id:str}" in paths
    # CallbackController routes
    assert "/callback/{payment_id:str}" in paths
    # RedirectController routes
    assert "/success/{payment_id:str}" in paths
    assert "/failure/{payment_id:str}" in paths


def test_create_payment_router_with_custom_registry() -> None:
    """Can pass a custom LitestarPluginRegistry."""
    custom_registry = LitestarPluginRegistry()

    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
        registry=custom_registry,
    )

    # The registry dependency provider should return our custom registry.
    registry_provider = router.dependencies["registry"]
    assert registry_provider.dependency() is custom_registry


def test_create_payment_router_with_order_resolver() -> None:
    """Can pass an order resolver."""
    resolver = AsyncMock()

    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
        order_resolver=resolver,
    )

    order_resolver_provider = router.dependencies["order_resolver"]
    assert order_resolver_provider.dependency() is resolver


def test_create_payment_router_dependencies() -> None:
    """Router has all expected dependencies configured."""
    config = _make_config()
    repo = AsyncMock()
    registry = LitestarPluginRegistry()
    resolver = AsyncMock()
    retry = AsyncMock()

    router = create_payment_router(
        config=config,
        repository=repo,
        registry=registry,
        order_resolver=resolver,
        retry_store=retry,
    )

    expected_keys = {
        "config",
        "repository",
        "registry",
        "order_resolver",
        "retry_store",
    }
    assert set(router.dependencies.keys()) == expected_keys

    # Verify each provider returns the correct object.
    assert router.dependencies["config"].dependency() is config
    assert router.dependencies["repository"].dependency() is repo
    assert router.dependencies["registry"].dependency() is registry
    assert router.dependencies["order_resolver"].dependency() is resolver
    assert router.dependencies["retry_store"].dependency() is retry


def test_create_payment_router_exception_handlers() -> None:
    """Router has exception handlers from the exceptions module."""
    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
    )

    assert router.exception_handlers == EXCEPTION_HANDLERS


def test_create_payment_router_default_registry() -> None:
    """Default LitestarPluginRegistry is created when none passed."""
    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
    )

    registry_provider = router.dependencies["registry"]
    created_registry = registry_provider.dependency()
    assert isinstance(created_registry, LitestarPluginRegistry)


def test_create_payment_router_none_optional_deps() -> None:
    """When optional deps are not passed, providers return None."""
    router = create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
    )

    assert router.dependencies["order_resolver"].dependency() is None
    assert router.dependencies["retry_store"].dependency() is None


def test_create_payment_router_calls_discover() -> None:
    """Registry discover() is called during router creation."""
    registry = LitestarPluginRegistry()
    assert not registry._discovered

    create_payment_router(
        config=_make_config(),
        repository=AsyncMock(),
        registry=registry,
    )

    assert registry._discovered
