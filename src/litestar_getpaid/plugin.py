"""Router factory for litestar-getpaid."""

from getpaid_core.protocols import PaymentRepository
from litestar import Router
from litestar.di import Provide

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import EXCEPTION_HANDLERS
from litestar_getpaid.protocols import CallbackRetryStore, OrderResolver
from litestar_getpaid.registry import LitestarPluginRegistry
from litestar_getpaid.routes.callbacks import CallbackController
from litestar_getpaid.routes.payments import PaymentController
from litestar_getpaid.routes.redirects import RedirectController


def create_payment_router(
    *,
    config: GetpaidConfig,
    repository: PaymentRepository,
    registry: LitestarPluginRegistry | None = None,
    order_resolver: OrderResolver | None = None,
    retry_store: CallbackRetryStore | None = None,
) -> Router:
    """Create a configured payment router.

    Args:
        config: Payment processing configuration.
        repository: Payment persistence backend.
        registry: Plugin registry. Creates a new one if not provided.
        order_resolver: Resolves order IDs to Order objects.
        retry_store: Storage for webhook retry queue.

    Returns:
        A Litestar Router with all payment endpoints.
    """
    actual_registry = registry or LitestarPluginRegistry()
    actual_registry.discover()

    return Router(
        path="/",
        route_handlers=[
            PaymentController,
            CallbackController,
            RedirectController,
        ],
        dependencies={
            "config": Provide(lambda: config, sync_to_thread=False),
            "repository": Provide(lambda: repository, sync_to_thread=False),
            "registry": Provide(lambda: actual_registry, sync_to_thread=False),
            "order_resolver": Provide(
                lambda: order_resolver, sync_to_thread=False
            ),
            "retry_store": Provide(lambda: retry_store, sync_to_thread=False),
        },
        exception_handlers=EXCEPTION_HANDLERS,
    )
