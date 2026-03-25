"""Litestar-aware plugin registry wrapper."""

from getpaid_core.registry import PluginRegistry


class LitestarPluginRegistry(PluginRegistry):
    """Plugin registry wrapper for Litestar adapter code."""
