# Catalog Runtime Schema and Authoring Guide

This guide defines the runtime catalog contract for `tin-canMCP`.

Use this when you want a split architecture:
- server/runtime repo: `tin-canMCP`
- catalog repo: tool manifests + generated `registry/*.json`

The runtime should treat the registry files as authoritative inputs.

## Required Registry Files

`catalog-runtime/registry/` must contain:
- `broker.json`
- `tools.json`
- `groups.json`
- `tiers.json`
- `aliases.json`
- `overlaps.json`
- `source_variants.json`

## Global Invariants

1. `tools[].name` must be unique.
2. `tools[].group` must exist in `groups[].name`.
3. `tools[].tier` must exist in `tiers` keys.
4. `aliases[].canonical_tool` must exist in `tools[].name`.
5. `overlaps[].canonical_tool` and all `members[]` must exist as either tool names or aliases.
6. `broker.strategy.default_active_groups` must be valid group names.
7. `broker.strategy.default_active_tiers` and `escalation_order` must be valid tier names.
8. `max_tools_per_activation` must be a positive integer.
9. `source_variants` are metadata only and should not create separate callable entries.

## File-by-File Contract

## `broker.json`
Purpose: defines startup activation behavior.

Required fields:
- `version` (integer)
- `strategy.default_active_groups` (string[])
- `strategy.default_active_tiers` (string[])
- `strategy.max_tools_per_activation` (integer > 0)
- `strategy.escalation_order` (string[]; usually `canonical`, `advanced`, `internal`)

Optional fields:
- `inventory` object for counters
- `routing_hints` for UX/agent hints

## `tools.json`
Purpose: canonical tool inventory.

Required fields per tool:
- `name` (string)
- `description` (string)
- `group` (string)
- `tier` (string)
- `status` (string; recommended values: `active`, `deprecated`, `disabled`)
- `canonical_tool` (string; usually self for canonical entries)
- `overlap_family` (string or null)
- `source_path` (string)
- `catalog_path` (string)
- `executable` (string)
- `priority` (integer)
- `default_exposed` (boolean)

Optional fields:
- `source_variants` (string[])
- `tags` (string[])
- `input_schema` (object)

## `groups.json`
Purpose: group-level routing and activation sizing.

Required fields per group:
- `name` (string)
- `description` (string)
- `activation_size` (integer > 0)
- `counts.total` / `counts.canonical` / `counts.advanced` / `counts.internal` (integers)
- `canonical_tools` / `advanced_tools` / `internal_tools` (string[])

Consistency rule:
- Group tool lists should match entries in `tools.json`.

## `tiers.json`
Purpose: global tier policy.

Object keys: tier names.
Each tier value should include:
- `description` (string)
- `default_visible` (boolean)

Recommended tiers:
- `canonical`
- `advanced`
- `internal`

## `aliases.json`
Purpose: canonical name mapping.

Required fields per alias object:
- `alias` (string)
- `canonical_tool` (string)

Rule:
- Alias names should not duplicate tool names.

## `overlaps.json`
Purpose: overlap-family dedupe policy.

Required fields per overlap:
- `family` (string)
- `canonical_tool` (string)
- `members` (string[])
- `note` (string)

Rule:
- `members` must include `canonical_tool`.

## `source_variants.json`
Purpose: provenance tracking.

Required fields per entry:
- `name` (string)
- `preferred_source_path` (string)
- `variant_source_path` (string)
- `reason` (string)

## Authoring Workflow

1. Collect source manifests from your source system.
2. Normalize tool names and fill `tools.json`.
3. Assign each tool to one group and one tier.
4. Define aliases and overlaps.
5. Set startup policy in `broker.json`.
6. Add provenance entries in `source_variants.json` when duplicates are merged.
7. Validate all cross-file references.

## JSON Schema Files

Machine-readable schemas are provided under `catalog-runtime/schema/`.
