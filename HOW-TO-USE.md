# How to use tin-canMCP

This is the prescriptive workflow for building a new MCP server from tin-canMCP. Follow the steps in order. Each step has a validation checkpoint.

## Mental model (read once, then refer back)

tin-canMCP splits into two layers:

1. **Runtime** (`app/catalog_runtime/` + `app/tools/`): already written. Do not modify. Exposes 7 broker tools to the AI client.
2. **Catalog** (`catalog-runtime/`): you author this. It's a registry of JSON files describing your domain tools.

The broker reads your registry at startup and gates which tools the AI can actually run via `catalog_run_tool`. Activation is group-based (domain) + tier-based (priority).

## Core concepts

- **Tool**: a single callable — a CLI command, API endpoint, AppleScript command, or SDK method.
- **Group**: a set of tools sharing a domain intent (e.g. `fs.read`, `billing.invoices`, `github.prs`).
- **Tier** (`canonical`, `advanced`, `internal`):
  - `canonical` — the default-visible tools. Most tasks should be solvable here.
  - `advanced` — specialized tools activated on demand via `catalog_escalate`.
  - `internal` — rare, edge-case, or alias-only tools. Normally hidden.
- **Alias**: a short name that resolves to a canonical tool (e.g. `rg` → `ripgrep`).
- **Overlap family**: a set of tools with near-duplicate function. The broker shows only the family's canonical member when the family is active.

## Step 1 — Decide your source type

Delegate to an AI using `ai-prompts/00-master-mcp-implementation.txt` (source-agnostic workflow). For source-specific nuances (naming conventions, default executables, security notes), paste `ai-prompts/source-hints.md` alongside.

Typical grouping starting points:

| Your integration is… | Typical grouping |
| --- | --- |
| OpenAPI / REST API | By business resource (`users`, `orders`, `billing.invoices`) |
| CLI binary / man pages | By user intent (`search`, `read`, `write`) |
| AppleScript dictionary | By app and action (`finder.files`, `mail.compose`) |
| SDK / library | By module or resource (`stripe.customers`, `s3.objects`) |
| Existing MCP to migrate | Copy then regroup by intent |

**Checkpoint**: you know the source type and approximate tool count.

## Step 2 — Scaffold the registry

```bash
python scripts/scaffold_catalog.py \
  --name <service> \
  --source <openapi|cli|applescript|sdk|custom> \
  --tools tool1,tool2,tool3,... \
  --group <optional-group-name> \
  --out catalog-runtime \
  --force
```

This generates all 7 registry files and placeholder manifests. All tools land in `canonical` initially — you will retier later.

**Checkpoint**: `python scripts/validate_registry.py catalog-runtime` prints `OK: registry valid`.

## Step 3 — Design your group taxonomy

Edit `catalog-runtime/registry/groups.json`. Goals:

- **Group by user intent, not by source origin.** If a user asks "find X", they shouldn't need to know whether X lives in `api.v1` or `api.v2` — they want `find`.
- **Keep `activation_size` ≤ 12.** If a group would blow past that, split it.
- **Name groups `<domain>.<action>`**. Examples: `fs.read`, `fs.write`, `billing.invoices`, `github.prs`.

For every group, also update:
- `description` — what intent this group serves
- `canonical_tools` / `advanced_tools` / `internal_tools` — explicit tool-to-tier membership
- `counts` — totals for each bucket

**Checkpoint**: every tool in `tools.json` appears in exactly one group bucket, and `validate_registry.py` still passes.

## Step 4 — Tier each tool

Edit the `tier` field on every entry in `tools.json`. Rules of thumb:

- **canonical** if it's in the common 80% of workflows for that group. Default-visible.
- **advanced** if it solves a real need but only for specialized queries (advanced flags, niche subcommands, esoteric resources).
- **internal** if it's a legacy alias, a near-duplicate, or a safety-sensitive tool you don't want the AI reaching for casually.

Move the file on disk too: `catalog-runtime/tools/<group>/<tier>/<name>.json`.

**Checkpoint**: canonical tool count per group ≈ 4–10. If >10, split the group.

## Step 5 — Declare aliases and overlaps

Edit `aliases.json` if any tool has a common short name:

```json
[
  {"alias": "rg", "canonical_tool": "ripgrep"}
]
```

Edit `overlaps.json` when two tools have near-identical function but you want one canonical representative:

```json
[
  {
    "family": "archive-family",
    "canonical_tool": "p7zip",
    "members": ["p7zip", "tar", "zip", "unzip", "gzip"],
    "note": "Archive / compression tools; expose p7zip by default."
  }
]
```

**Warning about overlap families**: the broker aggressively deduplicates. If a family has 6 members, the AI only sees 1 when that family is active. If you want all 6 visible, don't put them in an overlap family — use tiering instead.

**Checkpoint**: `validate_registry.py` still passes.

## Step 6 — Fill per-tool manifests

Edit each file in `catalog-runtime/tools/<group>/<tier>/<name>.json`. The manifest drives how `catalog_run_tool` builds the actual command:

```json
{
  "name": "ripgrep",
  "description": "Recursively search content by regex.",
  "executable": "/opt/homebrew/bin/rg",
  "invocation": {
    "binary": "/opt/homebrew/bin/rg",
    "positional_layout": [],
    "array_flag_style": "repeat the flag once per item",
    "boolean_flag_style": "include the flag only when true"
  },
  "inputSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "pattern":     {"type": "string",  "description": "regex pattern",      "flags": []},
      "ignore_case": {"type": "boolean", "description": "match case-insensitively", "flags": ["-i", "--ignore-case"]},
      "paths":       {"type": "array",   "items": {"type": "string"}, "description": "paths to search", "flags": []}
    },
    "required": ["pattern"]
  }
}
```

Key rules:
- `invocation.binary` — use absolute paths when possible for deterministic dispatch.
- Schema properties with `"flags": []` or no `flags` key are either positional or caller-supplied; list them in `positional_layout` or document them.
- Boolean props → flag appears only when `true`.
- Array props → flag repeats per item.
- Any `additionalProperties: false` schema rejects unknown keys.

**Checkpoint**: `python main.py --transport=stdio` starts cleanly. Calling `catalog_activate` on your group and then `catalog_run_tool` with a real tool name produces output.

## Step 7 — Configure broker strategy

Edit `catalog-runtime/registry/broker.json`:

- `default_active_groups` — which groups are live at startup. Keep this small (1–2 groups).
- `max_tools_per_activation` — hard cap on simultaneously visible tools. 12 is a good default.
- `routing_hints` — map intent strings to groups. **Add one hint per group.** This is how the AI decides what to activate.

Good routing hint:
```json
{"query_type": "create, read, update, or delete billing invoices", "activate_groups": ["billing.invoices"]}
```

**Checkpoint**: `catalog_status()` returns your hints; `catalog_activate` on every declared group succeeds.

## Step 8 — Ship

```bash
python scripts/validate_registry.py catalog-runtime  # must print OK
python -m compileall app main.py                     # must exit 0
python main.py --transport=stdio                     # must boot
```

Register the server in your MCP client config:

```json
{
  "mcpServers": {
    "mydomain": {
      "command": "/usr/local/bin/python3",
      "args": ["/abs/path/to/tin-canMCP/main.py", "--transport=stdio"],
      "env": {
        "VAR_CATALOG_RUNTIME_DIR": "/abs/path/to/tin-canMCP/catalog-runtime",
        "VAR_SERVER_NAME": "mydomain",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## Maintenance

- Adding tools: scaffold is one-shot; for incremental additions, edit `tools.json` + the group's bucket lists directly, add the manifest file, then validate.
- Renaming groups: update every occurrence in `tools.json`, `groups.json`, `broker.json`, and move the directory under `tools/`.
- When in doubt: run `validate_registry.py`.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Tool 'X' is not active` | X's group isn't activated, or X is in an active overlap family whose canonical is a different tool |
| `Unknown group(s): [...]` | You passed a group name not present in `groups.json` |
| `Manifest not found for X` | `catalog_path` in `tools.json` points nowhere and no fallback exists at `tools/<group>/<tier>/<name>.json` |
| `FileNotFoundError: Catalog runtime directory not found` | `VAR_CATALOG_RUNTIME_DIR` is wrong or the default path is missing |
| Server boots but no tools appear | `default_active_groups` is empty, or all tools in the default group are `status != "active"` |

## Further reading

- [docs/catalog-runtime-template.md](docs/catalog-runtime-template.md) — full schema contract
- [catalog-runtime/schema/](catalog-runtime/schema/) — machine-readable JSON Schemas
- [ai-prompts/00-master-mcp-implementation.txt](ai-prompts/00-master-mcp-implementation.txt) — master AI prompt
- [ai-prompts/source-hints.md](ai-prompts/source-hints.md) — per-source conventions
