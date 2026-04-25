from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CatalogRuntimeLoader:
    """Loads the 7 registry JSON files from a catalog-runtime directory.

    Expected layout:
        <runtime_dir>/registry/broker.json
        <runtime_dir>/registry/groups.json
        <runtime_dir>/registry/tiers.json
        <runtime_dir>/registry/tools.json
        <runtime_dir>/registry/aliases.json
        <runtime_dir>/registry/overlaps.json
        <runtime_dir>/registry/source_variants.json

    Optional per-tool manifests may live at:
        <runtime_dir>/tools/<group>/<tier>/<name>.json
    """

    def __init__(self, runtime_dir: str):
        self.runtime_dir = Path(runtime_dir).expanduser().resolve()
        self.registry_dir = self.runtime_dir / "registry"

    def load(self) -> dict[str, Any]:
        data = {
            "broker": self._load_json(self.registry_dir / "broker.json"),
            "groups": self._load_json(self.registry_dir / "groups.json"),
            "tiers": self._load_json(self.registry_dir / "tiers.json"),
            "tools": self._load_json(self.registry_dir / "tools.json"),
            "aliases": self._load_json(self.registry_dir / "aliases.json"),
            "overlaps": self._load_json(self.registry_dir / "overlaps.json"),
            "source_variants": self._load_json(self.registry_dir / "source_variants.json"),
        }
        self._validate(data)
        return data

    def load_manifest(self, catalog_path: str, group: str, tier: str, name: str) -> dict[str, Any]:
        direct = Path(catalog_path)
        if direct.exists():
            return self._load_json(direct)

        fallback = self.runtime_dir / "tools" / group / tier / f"{name}.json"
        if fallback.exists():
            return self._load_json(fallback)

        raise FileNotFoundError(f"Manifest not found for {name}: {direct}")

    @staticmethod
    def _load_json(path: Path) -> Any:
        return json.loads(path.read_text())

    def _validate(self, data: dict[str, Any]) -> None:
        if not self.runtime_dir.exists():
            raise FileNotFoundError(f"Catalog runtime directory not found: {self.runtime_dir}")

        required = ["broker", "groups", "tiers", "tools", "aliases", "overlaps", "source_variants"]
        missing = [name for name in required if name not in data]
        if missing:
            raise ValueError(f"Missing required registry payloads: {missing}")

        if not isinstance(data["tools"], list):
            raise ValueError("registry/tools.json must be a list")

        for entry in data["tools"]:
            for key in ("name", "group", "tier", "canonical_tool", "catalog_path", "executable"):
                if key not in entry:
                    raise ValueError(f"Tool entry missing '{key}': {entry}")
