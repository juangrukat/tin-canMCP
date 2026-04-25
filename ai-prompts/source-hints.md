# Source-type hints

Paste alongside `00-master-mcp-implementation.txt` when your source is one of these. These are addenda, not replacements — the master prompt already handles the generic workflow.

## OpenAPI / REST API

- **Tool naming**: `<resource>-<verb>` (`users-list`, `orders-create`). Verb before noun reads worse in catalog search.
- **Grouping**: by business resource, not URL path. `/api/v2/customers/{id}/invoices` → group `billing.invoices`, not `api.v2`.
- **Tiering**: GET → `canonical`; POST/PUT/PATCH → `canonical` only if the action is common and non-destructive; DELETE → `advanced` minimum, `internal` for bulk/admin endpoints.
- **Executable**: set to your HTTP adapter path (custom Python wrapper). The broker's `ToolExecutor` runs subprocesses — for pure-API MCPs you may need a thin wrapper binary or to bypass the executor and call HTTP directly from a custom tool. Document this choice.
- **Auth**: read from env via `app/config.py` settings; never embed keys in manifests.

## CLI / man pages

- **Tool naming**: `<cli>-<subcommand>` when the CLI has subcommands (`git-status`, `docker-ps`); plain `<cli>` when it's a single binary (`rg`, `fd`, `jq`).
- **Executable**: absolute path (`/opt/homebrew/bin/rg`), not `rg`. Avoid PATH surprises.
- **inputSchema**: derive `flags` arrays directly from the man page. Include both short and long forms; the executor picks the long flag by preference.
- **Tiering**: safe read-oriented subcommands → `canonical`; `--force`, `--recursive`, migration commands → `advanced`; destructive ones (`rm -rf`-class) → `internal`.
- **Overlap families**: group near-duplicate tools (e.g. `grep` / `rg` / `ag`) with one canonical.

## AppleScript dictionary

- **Tool naming**: `<app>-<action>` (`finder-open`, `mail-compose`).
- **Executable**: always `/usr/bin/osascript`. The tool's AppleScript body lives in the manifest's `invocation.examples` or a custom field; you'll need a tiny shim that renders the script from args.
- **Tiering**: read-only queries (`get`, `list`, `exists`) → `canonical`; state changes (`move`, `delete`, `mount`) → `advanced`; anything that touches System Events or requires Automation permissions → `internal` (document the permission grant in the tool description).
- **Return shape**: AppleScript output is stringly-typed. If your tool parses the result, normalize in a wrapper script rather than teaching the AI to re-parse every time.

## SDK / library

- **First question**: does the SDK run in-process or does it need a subprocess shim? The default `ToolExecutor` assumes subprocess. For in-process SDKs, you'll either build a CLI wrapper (`python -m mysdk ...`) or extend the runtime with a direct-call executor. Pick one and document.
- **Tool naming**: `<sdk>-<method>` or `<resource>-<verb>`.
- **Pin versions**: note exact SDK version in the tool `description` so breakage is traceable.
- **Don't expose internals**: if the SDK has `_private` methods, don't catalog them — they'll churn.

## Existing MCP migration

- **Inventory first**: dump the old server's tool list (`tools/list` MCP call). That's your raw input.
- **Rename cautiously**: if you change a tool name, add it to `aliases.json` pointing to the canonical. Don't break existing clients silently.
- **Overlap opportunity**: migrations often reveal redundant tools. Use `overlaps.json` to collapse them; the canonical gets picked automatically.
- **Keep `source_variants.json` populated**: record which original tool each catalog entry came from. Useful for audits and rollback.

## Hybrid (MCP + API + CLI in one catalog)

- **Segregate by group, not by source**: the AI shouldn't need to know that `billing.invoices` is backed partly by API calls and partly by a CLI. Keep the split invisible in the catalog, implement it in per-tool manifests.
- **Consistent `inputSchema` conventions**: one tool's `limit` should behave the same regardless of its backing source. Normalize at the manifest layer.
