"""Tests for the Litestar-aware plugin registry wrapper."""

import pytest
from getpaid_core.processor import BaseProcessor
from getpaid_core.types import TransactionResult


class FakeProcessor(BaseProcessor):
    slug = "fake"
    display_name = "Fake Backend"
    accepted_currencies = ["PLN", "EUR"]

    async def prepare_transaction(self, **kwargs) -> TransactionResult:
        return TransactionResult(
            redirect_url="https://example.com",
            form_data=None,
            method="GET",
            headers={},
        )


def test_litestar_registry_register_and_get():
    """Can register and retrieve a processor."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    reg.register(FakeProcessor)
    assert reg.get_by_slug("fake") is FakeProcessor


def test_litestar_registry_get_for_currency():
    """Can find processors by currency."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    reg.register(FakeProcessor)
    backends = reg.get_for_currency("PLN")
    assert FakeProcessor in backends


def test_litestar_registry_get_choices():
    """Returns slug/name pairs for a currency."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    reg.register(FakeProcessor)
    choices = reg.get_choices("PLN")
    assert ("fake", "Fake Backend") in choices


def test_litestar_registry_unknown_slug_raises():
    """KeyError for unknown slug."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    with pytest.raises(KeyError):
        reg.get_by_slug("nonexistent")


def test_litestar_registry_discover():
    """Discover delegates to core registry and copies backends."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    reg.register(FakeProcessor)
    assert reg.get_by_slug("fake") is FakeProcessor


def test_litestar_registry_unregister():
    """Can unregister a backend."""
    from litestar_getpaid.registry import LitestarPluginRegistry

    reg = LitestarPluginRegistry()
    reg.register(FakeProcessor)
    reg.unregister("fake")
    with pytest.raises(KeyError):
        reg.get_by_slug("fake")
