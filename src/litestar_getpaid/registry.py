"""Litestar-aware plugin registry wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from getpaid_core.registry import PluginRegistry

if TYPE_CHECKING:
    from litestar import Router


class LitestarPluginRegistry(PluginRegistry):
    """Plugin registry with Litestar-specific features.

    Wraps the core PluginRegistry and adds router mounting
    for backend-specific callback routes.
    """

    def __init__(self) -> None:
        super().__init__()
        self._backend_routers: dict[str, Router] = {}

    def register_backend_router(
        self,
        slug: str,
        router: Router,
    ) -> None:
        """Register a Litestar Router for a backend's custom routes."""
        self._backend_routers[slug] = router

    def get_backend_router(self, slug: str) -> Router | None:
        """Get a backend's custom Router, if registered."""
        return self._backend_routers.get(slug)

    def get_all_backend_routers(self) -> dict[str, Router]:
        """Return all registered backend routers."""
        return dict(self._backend_routers)
