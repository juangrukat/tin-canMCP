"""Tool registration for tin-canMCP.

The template is prescriptive: every tin-canMCP server exposes the same 7
broker-level MCP tools. The actual domain tools live in the catalog and are
surfaced through `catalog_run_tool`. This keeps the visible tool count bounded
no matter how large the catalog grows.

You should NOT add @mcp.tool() entries here for your domain tools. Instead,
author registry JSON in `catalog-runtime/registry/` and per-tool manifests in
`catalog-runtime/tools/<group>/<tier>/<name>.json`. See HOW-TO-USE.md.

If you truly need a non-catalog tool (e.g. a custom orchestration shim), add
it in a separate module and register it below the `register_catalog_tools`
call — but prefer the catalog path.
"""

from app.tools.catalog_tools import register_catalog_tools


def register_tools(mcp):
    register_catalog_tools(mcp)
