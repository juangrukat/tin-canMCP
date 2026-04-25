from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ActivationState:
    groups: list[str]
    tiers: list[str]


class CatalogBroker:
    """Runtime broker that manages which tools are 'active' (visible to callers).

    The broker enforces three concerns:
      1. Group-based activation — only tools in active groups are runnable.
      2. Tier-based escalation — canonical by default, advanced/internal on demand.
      3. Overlap-family deduplication — avoid exposing near-duplicate tools.
    """

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        self.tools = payload["tools"]
        self.groups = payload["groups"]
        self.tiers = payload["tiers"]
        self.alias_pairs = payload["aliases"]
        self.overlaps = payload["overlaps"]

        strategy = payload["broker"]["strategy"]
        self.max_tools = int(strategy["max_tools_per_activation"])
        self.escalation_order = list(strategy["escalation_order"])

        self.alias_to_canonical = {a["alias"]: a["canonical_tool"] for a in self.alias_pairs}
        self.group_names = {g["name"] for g in self.groups}
        self.tier_names = set(self.tiers.keys())

        self.overlap_family_by_tool: dict[str, str] = {}
        self.overlap_canonical: dict[str, str] = {}
        for family in self.overlaps:
            fam_name = family["family"]
            self.overlap_canonical[fam_name] = family["canonical_tool"]
            for member in family["members"]:
                self.overlap_family_by_tool[member] = fam_name

        self.state = ActivationState(
            groups=list(strategy["default_active_groups"]),
            tiers=list(strategy["default_active_tiers"]),
        )
        self.active_tools = self._compute_active_tools()

    def resolve_name(self, name: str) -> str:
        return self.alias_to_canonical.get(name, name)

    def set_activation(self, groups: list[str] | None = None, tiers: list[str] | None = None, mode: str = "replace") -> dict[str, Any]:
        if groups is not None:
            self._validate_groups(groups)
            if mode == "add":
                current = set(self.state.groups)
                current.update(groups)
                self.state.groups = sorted(current)
            else:
                self.state.groups = list(groups)

        if tiers is not None:
            self._validate_tiers(tiers)
            if mode == "add":
                current = set(self.state.tiers)
                current.update(tiers)
                self.state.tiers = [t for t in self.escalation_order if t in current]
            else:
                self.state.tiers = list(tiers)

        self.active_tools = self._compute_active_tools()
        return self.status()

    def escalate(self) -> dict[str, Any]:
        current = set(self.state.tiers)
        next_tier = None
        for tier in self.escalation_order:
            if tier not in current:
                next_tier = tier
                break

        if next_tier is None:
            return {"changed": False, "reason": "already at highest tier", **self.status()}

        current.add(next_tier)
        self.state.tiers = [tier for tier in self.escalation_order if tier in current]
        self.active_tools = self._compute_active_tools()
        return {"changed": True, "added_tier": next_tier, **self.status()}

    def status(self) -> dict[str, Any]:
        return {
            "active_groups": self.state.groups,
            "active_tiers": self.state.tiers,
            "active_tool_count": len(self.active_tools),
            "max_tools_per_activation": self.max_tools,
        }

    def list_active_tools(self) -> list[dict[str, Any]]:
        return list(self.active_tools.values())

    def search_tools(
        self,
        query: str = "",
        groups: list[str] | None = None,
        tiers: list[str] | None = None,
        limit: int = 20,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        query_lc = query.lower().strip()
        candidates = list(self.active_tools.values()) if active_only else list(self.tools)

        if groups:
            self._validate_groups(groups)
            allowed_groups = set(groups)
            candidates = [c for c in candidates if c["group"] in allowed_groups]

        if tiers:
            self._validate_tiers(tiers)
            allowed_tiers = set(tiers)
            candidates = [c for c in candidates if c["tier"] in allowed_tiers]

        ranked = []
        for tool in candidates:
            text = f"{tool['name']} {tool.get('description', '')}".lower()
            if not query_lc:
                score = 0
            elif tool["name"].lower() == query_lc:
                score = 100
            elif query_lc in tool["name"].lower():
                score = 75
            elif query_lc in text:
                score = 40
            else:
                continue
            ranked.append((score, int(tool.get("priority", 0)), tool["name"], tool))

        ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return [entry[3] for entry in ranked[: max(1, min(limit, 200))]]

    def get_tool(self, name: str) -> dict[str, Any] | None:
        canonical = self.resolve_name(name)
        for tool in self.tools:
            if tool["name"] == canonical:
                return tool
        return None

    def ensure_active(self, name: str) -> dict[str, Any]:
        canonical = self.resolve_name(name)
        tool = self.active_tools.get(canonical)
        if tool is None:
            raise ValueError(
                f"Tool '{name}' is not active. Use catalog_activate or catalog_escalate first."
            )
        return tool

    def _compute_active_tools(self) -> dict[str, dict[str, Any]]:
        selected = [
            t
            for t in self.tools
            if t.get("status", "active") == "active"
            and t["group"] in self.state.groups
            and t["tier"] in self.state.tiers
        ]
        selected.sort(
            key=lambda t: (
                int(t.get("priority", 0)),
                bool(t.get("default_exposed", False)),
                t["name"],
            ),
            reverse=True,
        )

        by_name: dict[str, dict[str, Any]] = {}
        for tool in selected:
            if tool["name"] != tool.get("canonical_tool", tool["name"]):
                continue
            by_name.setdefault(tool["name"], tool)

        deduped: dict[str, dict[str, Any]] = {}
        taken_families: set[str] = set()
        for tool in by_name.values():
            family = self.overlap_family_by_tool.get(tool["name"])
            if family is None:
                deduped[tool["name"]] = tool
                continue

            if family in taken_families:
                continue

            canonical = self.overlap_canonical.get(family)
            if canonical and canonical in by_name:
                deduped[canonical] = by_name[canonical]
            else:
                deduped[tool["name"]] = tool
            taken_families.add(family)

        final = list(deduped.values())
        final.sort(
            key=lambda t: (
                int(t.get("priority", 0)),
                bool(t.get("default_exposed", False)),
                t["name"],
            ),
            reverse=True,
        )
        final = final[: self.max_tools]

        return {t["name"]: t for t in final}

    def _validate_groups(self, groups: list[str]) -> None:
        unknown = sorted(set(groups) - self.group_names)
        if unknown:
            raise ValueError(f"Unknown group(s): {unknown}")

    def _validate_tiers(self, tiers: list[str]) -> None:
        unknown = sorted(set(tiers) - self.tier_names)
        if unknown:
            raise ValueError(f"Unknown tier(s): {unknown}")
