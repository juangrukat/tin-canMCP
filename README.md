# tin-canMCP

A prescriptive template for building **large** MCP servers (20+ tools) organized as a tiered catalog with a broker.

Every tin-canMCP server exposes **exactly 7 tools** to the AI client, regardless of catalog size. The catalog itself can contain hundreds of tools; the broker gates visibility so the AI only sees a bounded, task-relevant subset at any moment.

## When to use this template

Use tin-canMCP when your MCP will wrap **many** tools (CLI binaries, API endpoints, AppleScript commands, SDK methods). The broker pattern keeps the AI's visible tool count under a cache-friendly ceiling.

Do NOT use tin-canMCP if you only need 3–10 tools with no grouping. A plain FastMCP server is simpler.

## The 7 tools every server exposes

| Tool | Purpose |
| --- | --- |
| `catalog_status` | Show current activation state and routing hints |
| `catalog_list_groups` | List every group in the catalog |
| `catalog_search_tools` | Search the full catalog by name/description (no activation needed) |
| `catalog_activate` | Turn on groups/tiers so their tools become runnable |
| `catalog_escalate` | Widen activation to the next tier (canonical → advanced → internal) |
| `catalog_active_tools` | Show which tools are currently runnable |
| `catalog_run_tool` | Execute an active tool by name with args |

Domain tools are reached only through `catalog_run_tool`. See [HOW-TO-USE.md](HOW-TO-USE.md) for the full workflow.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env

# Scaffold a catalog for your domain
python scripts/scaffold_catalog.py \
  --name mydomain \
  --source cli \
  --tools list,get,create,delete \
  --out catalog-runtime \
  --force

# Validate the registry is structurally sound
python scripts/validate_registry.py catalog-runtime

# Run the server
python main.py --transport=stdio
```

At this point the server loads, exposes the 7 broker tools, and `catalog_run_tool` will refuse to run anything until you fill in the `TODO` markers in `catalog-runtime/registry/tools.json` and the per-tool manifests under `catalog-runtime/tools/`.

**Next**: read [HOW-TO-USE.md](HOW-TO-USE.md) — it walks through authoring tool manifests, grouping strategies, and tier assignment.

## Repository layout

```text
.
├── app/
│   ├── catalog_runtime/     # Broker, loader, executor (DO NOT modify)
│   ├── tools/               # Registers the 7 broker MCP tools (DO NOT modify)
│   ├── prompts/             # Optional MCP prompts
│   ├── config.py            # Env-backed settings
│   └── server.py            # FastMCP server
├── catalog-runtime/
│   ├── registry/            # YOUR 7 registry JSON files — edit these
│   ├── tools/               # YOUR per-tool manifests — edit these
│   └── schema/              # JSON Schemas for registry files (reference)
├── scripts/
│   ├── scaffold_catalog.py  # Generate a registry skeleton
│   └── validate_registry.py # Check invariants (run in CI)
├── ai-prompts/              # Master prompt + per-source hints for AI implementation
├── docs/
│   └── catalog-runtime-template.md  # Full schema contract reference
├── main.py
└── HOW-TO-USE.md            # Prescriptive authoring workflow
```

## Configuration

Environment variables (via `.env` or shell):

- `VAR_CATALOG_RUNTIME_DIR` — path to your catalog runtime (default: repo-local `catalog-runtime/`)
- `VAR_SERVER_NAME` — MCP server name shown to clients (default: `tin-canMCP`)
- `VAR_COMMAND_TIMEOUT_SECONDS` — per-tool timeout (default: `20`)
- `VAR_MAX_OUTPUT_CHARS` — truncation threshold for stdout/stderr (default: `12000`)
- `MCP_TRANSPORT` — `stdio`, `sse`, or `web` (default: `stdio`)

## What NOT to do

- **Do not** add `@mcp.tool()` decorators for your domain tools in `app/tools/`. That defeats the broker. Add catalog entries instead.
- **Do not** raise `max_tools_per_activation` above ~15. The whole point is a bounded visible surface.
- **Do not** put every tool in `canonical`. Use `advanced` and `internal` tiers to defer niche tools.
- **Do not** skip `validate_registry.py`. Cross-reference bugs are silent.

## License

MIT. See `LICENSE`.
