#!/usr/bin/env python3
"""Validate every cross-reference invariant in a catalog-runtime registry.

Usage:
    python scripts/validate_registry.py [runtime_dir]

Exits 0 on success, non-zero on failure. Run in CI or pre-commit.

Invariants checked (matching docs/catalog-runtime-template.md):
    1. registry/ directory exists with all 7 JSON files.
    2. tools[].name is unique.
    3. tools[].group exists in groups[].name.
    4. tools[].tier exists in tiers keys.
    5. aliases[].canonical_tool exists in tools[].name.
    6. aliases[].alias does not collide with a tool name.
    7. overlaps[].canonical_tool exists and is in its members list.
    8. overlaps[].members are all known tool names or aliases.
    9. broker.strategy.default_active_groups are valid group names.
   10. broker.strategy.default_active_tiers and escalation_order are valid tier names.
   11. broker.strategy.max_tools_per_activation is a positive integer.
   12. group.canonical_tools / advanced_tools / internal_tools match tools.json membership.
   13. Each tool's catalog_path (if present) is reachable on disk, or a fallback manifest exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FILES = [
    "broker.json",
    "groups.json",
    "tiers.json",
    "tools.json",
    "aliases.json",
    "overlaps.json",
    "source_variants.json",
]


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors

    def print_report(self) -> None:
        for w in self.warnings:
            print(f"WARN:  {w}")
        for e in self.errors:
            print(f"ERROR: {e}")
        if self.ok():
            print(f"OK: registry valid ({len(self.warnings)} warnings)")
        else:
            print(f"FAIL: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def validate(runtime_dir: Path, report: Reporter) -> None:
    registry = runtime_dir / "registry"
    if not registry.is_dir():
        report.error(f"registry dir not found: {registry}")
        return

    payload: dict[str, object] = {}
    for fname in REQUIRED_FILES:
        fpath = registry / fname
        if not fpath.is_file():
            report.error(f"missing registry file: {fpath}")
            continue
        try:
            payload[fname[:-5]] = load_json(fpath)
        except json.JSONDecodeError as exc:
            report.error(f"invalid JSON in {fpath}: {exc}")

    if not report.ok():
        return

    tools = payload["tools"]
    groups = payload["groups"]
    tiers = payload["tiers"]
    aliases = payload["aliases"]
    overlaps = payload["overlaps"]
    broker = payload["broker"]

    if not isinstance(tools, list):
        report.error("tools.json must be a list")
        return
    if not isinstance(groups, list):
        report.error("groups.json must be a list")
        return
    if not isinstance(tiers, dict):
        report.error("tiers.json must be an object")
        return

    tool_names = set()
    for t in tools:
        name = t.get("name")
        if not name:
            report.error(f"tool without name: {t}")
            continue
        if name in tool_names:
            report.error(f"duplicate tool name: {name}")
        tool_names.add(name)

    group_names = {g["name"] for g in groups if "name" in g}
    tier_names = set(tiers.keys())

    for t in tools:
        name = t.get("name", "?")
        g = t.get("group")
        if g not in group_names:
            report.error(f"tool '{name}' references unknown group '{g}'")
        if t.get("tier") not in tier_names:
            report.error(f"tool '{name}' references unknown tier '{t.get('tier')}'")
        ct = t.get("canonical_tool")
        if ct and ct not in tool_names:
            report.error(f"tool '{name}' canonical_tool '{ct}' is not a known tool")

    alias_names = set()
    for a in aliases:
        alias = a.get("alias")
        canonical = a.get("canonical_tool")
        if not alias or not canonical:
            report.error(f"alias entry missing fields: {a}")
            continue
        if alias in tool_names:
            report.error(f"alias '{alias}' collides with a tool name")
        if canonical not in tool_names:
            report.error(f"alias '{alias}' points to unknown tool '{canonical}'")
        alias_names.add(alias)

    known_refs = tool_names | alias_names
    for fam in overlaps:
        fname = fam.get("family", "?")
        canonical = fam.get("canonical_tool")
        members = fam.get("members", [])
        if canonical not in tool_names:
            report.error(f"overlap '{fname}' canonical_tool '{canonical}' not a tool")
        if canonical not in members:
            report.error(f"overlap '{fname}' canonical_tool '{canonical}' missing from members")
        for m in members:
            if m not in known_refs:
                report.error(f"overlap '{fname}' member '{m}' is not a known tool or alias")

    strategy = broker.get("strategy", {}) if isinstance(broker, dict) else {}
    for g in strategy.get("default_active_groups", []):
        if g not in group_names:
            report.error(f"broker default_active_groups references unknown group '{g}'")
    for tr in strategy.get("default_active_tiers", []):
        if tr not in tier_names:
            report.error(f"broker default_active_tiers references unknown tier '{tr}'")
    for tr in strategy.get("escalation_order", []):
        if tr not in tier_names:
            report.error(f"broker escalation_order references unknown tier '{tr}'")
    max_tools = strategy.get("max_tools_per_activation")
    if not isinstance(max_tools, int) or max_tools <= 0:
        report.error(f"broker max_tools_per_activation must be positive int, got {max_tools!r}")

    tools_by_name = {t["name"]: t for t in tools if "name" in t}
    for g in groups:
        gname = g.get("name", "?")
        for bucket in ("canonical_tools", "advanced_tools", "internal_tools"):
            for n in g.get(bucket, []):
                if n not in tools_by_name:
                    report.error(f"group '{gname}' {bucket} references unknown tool '{n}'")
                    continue
                entry = tools_by_name[n]
                expected_tier = bucket.replace("_tools", "")
                if entry.get("tier") != expected_tier:
                    report.warn(
                        f"group '{gname}' lists '{n}' as {expected_tier} but tools.json says tier '{entry.get('tier')}'"
                    )

    # Manifest reachability (warn, not error — catalog_path may be a placeholder)
    for t in tools:
        cp = t.get("catalog_path")
        name = t.get("name")
        if not cp:
            continue
        direct = Path(cp)
        fallback = runtime_dir / "tools" / t.get("group", "") / t.get("tier", "") / f"{name}.json"
        if not direct.is_file() and not fallback.is_file():
            report.warn(f"tool '{name}': catalog_path not found on disk ({cp}) and no fallback at {fallback}")


def main() -> int:
    argv = sys.argv[1:]
    runtime_dir = Path(argv[0] if argv else "catalog-runtime").resolve()
    print(f"Validating: {runtime_dir}")
    report = Reporter()
    validate(runtime_dir, report)
    report.print_report()
    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
