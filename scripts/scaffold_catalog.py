#!/usr/bin/env python3
"""Scaffold a new catalog-runtime from a source inventory.

Usage:
    python scripts/scaffold_catalog.py \\
        --name my-service \\
        --source openapi|cli|applescript|sdk|custom \\
        --tools tool1,tool2,tool3 \\
        --group <group-name> \\
        --out catalog-runtime

This generates the 7 registry JSON files with canonical tier for every tool
you list, and empty advanced/internal tiers you can populate later. The output
is a VALID registry that passes `scripts/validate_registry.py`.

Follow-ups after scaffolding (in order):
    1. Edit registry/groups.json to add more groups + tier your tools.
    2. Move tools to advanced/internal tiers if they are specialized or rare.
    3. Fill registry/aliases.json with short-name aliases (optional).
    4. Fill registry/overlaps.json with duplicate-dedupe families (optional).
    5. Author per-tool manifests in tools/<group>/<tier>/<name>.json.
    6. Run: python scripts/validate_registry.py <out>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TIERS_DEFAULT = {
    "canonical": {
        "description": "Preferred default exposure surface for first-pass tool selection.",
        "default_visible": True,
    },
    "advanced": {
        "description": "Useful tools activated only when the query is specific enough.",
        "default_visible": False,
    },
    "internal": {
        "description": "Rare or edge-case tools normally hidden from routing.",
        "default_visible": False,
    },
}


def build_broker(group_name: str) -> dict:
    return {
        "version": 1,
        "strategy": {
            "default_active_groups": [group_name],
            "default_active_tiers": ["canonical"],
            "max_tools_per_activation": 12,
            "escalation_order": ["canonical", "advanced", "internal"],
        },
        "inventory": {
            "unique_tool_names": 0,
            "group_count": 1,
            "alias_count": 0,
            "source_variant_count": 0,
        },
        "routing_hints": [
            {
                "query_type": f"default queries for {group_name}",
                "activate_groups": [group_name],
            }
        ],
    }


def build_groups(group_name: str, tool_names: list[str]) -> list[dict]:
    return [
        {
            "name": group_name,
            "description": f"Default group for {group_name} tools. Edit this description.",
            "activation_size": min(12, max(4, len(tool_names))),
            "counts": {
                "total": len(tool_names),
                "canonical": len(tool_names),
                "advanced": 0,
                "internal": 0,
            },
            "canonical_tools": sorted(tool_names),
            "advanced_tools": [],
            "internal_tools": [],
        }
    ]


def build_tools(group_name: str, tool_names: list[str], out_root: Path) -> list[dict]:
    priority = 100
    entries = []
    for name in tool_names:
        catalog_path = out_root / "tools" / group_name / "canonical" / f"{name}.json"
        entries.append(
            {
                "name": name,
                "description": f"TODO: describe {name}.",
                "group": group_name,
                "tier": "canonical",
                "status": "active",
                "canonical_tool": name,
                "overlap_family": None,
                "source_path": f"TODO/source/{name}",
                "catalog_path": str(catalog_path.resolve()),
                "executable": name,
                "priority": priority,
                "default_exposed": True,
            }
        )
        priority = max(40, priority - 5)
    return entries


def build_tool_manifest(name: str) -> dict:
    return {
        "name": name,
        "description": f"TODO: describe {name}",
        "executable": name,
        "invocation": {
            "binary": name,
            "positional_layout": [],
            "array_flag_style": "repeat the flag once per item",
            "boolean_flag_style": "include the flag only when true",
            "examples": [],
        },
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "required": [],
        },
    }


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold a catalog-runtime registry.")
    p.add_argument("--name", required=True, help="Service / integration name (used for defaults).")
    p.add_argument(
        "--source",
        choices=("openapi", "cli", "applescript", "sdk", "custom"),
        default="custom",
        help="Source type the catalog is derived from (informational; sets a TODO marker).",
    )
    p.add_argument(
        "--tools",
        required=True,
        help="Comma-separated list of initial tool names (all placed in canonical).",
    )
    p.add_argument(
        "--group",
        default=None,
        help="Group name (defaults to <name>.main).",
    )
    p.add_argument(
        "--out",
        default="catalog-runtime",
        help="Output runtime directory (default: catalog-runtime).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing registry files if present.",
    )
    args = p.parse_args()

    tool_names = [n.strip() for n in args.tools.split(",") if n.strip()]
    if not tool_names:
        print("ERROR: --tools must list at least one tool name", file=sys.stderr)
        return 2

    group_name = args.group or f"{args.name}.main"
    out_root = Path(args.out).resolve()
    registry = out_root / "registry"

    if registry.exists() and any(registry.iterdir()) and not args.force:
        print(f"ERROR: {registry} is not empty. Pass --force to overwrite.", file=sys.stderr)
        return 2

    broker = build_broker(group_name)
    broker["inventory"]["unique_tool_names"] = len(tool_names)

    groups = build_groups(group_name, tool_names)
    tools = build_tools(group_name, tool_names, out_root)

    write_json(registry / "broker.json", broker)
    write_json(registry / "groups.json", groups)
    write_json(registry / "tiers.json", TIERS_DEFAULT)
    write_json(registry / "tools.json", tools)
    write_json(registry / "aliases.json", [])
    write_json(registry / "overlaps.json", [])
    write_json(registry / "source_variants.json", [])

    for name in tool_names:
        mf_path = out_root / "tools" / group_name / "canonical" / f"{name}.json"
        write_json(mf_path, build_tool_manifest(name))

    print(f"Scaffolded catalog at: {out_root}")
    print(f"  group: {group_name}")
    print(f"  tools ({len(tool_names)}): {', '.join(tool_names)}")
    print(f"  source type: {args.source}")
    print("\nNext steps:")
    print("  1. Edit TODO markers in registry/tools.json (descriptions, executables, source_path).")
    print(f"  2. Fill inputSchema and invocation for each manifest in {out_root}/tools/...")
    print("  3. Split tools into advanced/internal tiers in groups.json as appropriate.")
    print(f"  4. Validate: python scripts/validate_registry.py {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
