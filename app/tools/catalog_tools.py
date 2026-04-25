"""Registers the 7 broker-level MCP tools.

These tools are the ONLY tools the AI client sees. Actual catalog tools are
reached via `catalog_run_tool` after activation. This keeps the visible surface
tiny regardless of catalog size.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.catalog_runtime import CatalogBroker, CatalogRuntimeLoader, ToolExecutor


_loader = CatalogRuntimeLoader(settings.catalog_runtime_dir)
_payload = _loader.load()
_broker = CatalogBroker(_payload)
_executor = ToolExecutor(
    loader=_loader,
    default_timeout_seconds=settings.command_timeout_seconds,
    max_output_chars=settings.max_output_chars,
)


def register_catalog_tools(mcp) -> None:
    @mcp.tool()
    async def catalog_status() -> dict[str, Any]:
        """Return runtime catalog status and current activation state."""
        status = _broker.status()
        status.update(
            {
                "runtime_dir": settings.catalog_runtime_dir,
                "server": settings.server_name,
                "routing_hints": _payload["broker"].get("routing_hints", []),
            }
        )
        return status

    @mcp.tool()
    async def catalog_list_groups() -> list[dict[str, Any]]:
        """List every group and its tier counts."""
        return _payload["groups"]

    @mcp.tool()
    async def catalog_activate(
        groups: list[str],
        tiers: list[str] | None = None,
        mode: str = "replace",
    ) -> dict[str, Any]:
        """Activate broker groups/tiers. mode is 'replace' (default) or 'add'."""
        if mode not in {"replace", "add"}:
            raise ValueError("mode must be 'replace' or 'add'")
        return _broker.set_activation(groups=groups, tiers=tiers, mode=mode)

    @mcp.tool()
    async def catalog_escalate() -> dict[str, Any]:
        """Escalate active tiers using the broker escalation order."""
        return _broker.escalate()

    @mcp.tool()
    async def catalog_active_tools() -> list[dict[str, Any]]:
        """Show currently active tools after canonical + overlap filtering."""
        return _broker.list_active_tools()

    @mcp.tool()
    async def catalog_search_tools(
        query: str = "",
        groups: list[str] | None = None,
        tiers: list[str] | None = None,
        limit: int = 20,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Search the full catalog by name/description; no activation required."""
        return _broker.search_tools(
            query=query,
            groups=groups,
            tiers=tiers,
            limit=limit,
            active_only=active_only,
        )

    @mcp.tool()
    async def catalog_run_tool(
        name: str,
        args: dict[str, Any] | None = None,
        positional: list[str] | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Run an active catalog tool by name using manifest-driven argv construction."""
        tool = _broker.ensure_active(name)
        return _executor.run(
            tool_record=tool,
            args=args,
            positional=positional,
            timeout_seconds=timeout_seconds,
        )
