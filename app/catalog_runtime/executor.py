from __future__ import annotations

import subprocess
import time
from typing import Any

from app.catalog_runtime.loader import CatalogRuntimeLoader


class ToolExecutor:
    """Executes a catalog tool by building argv from the tool's manifest + caller args.

    Manifest conventions (see HOW-TO-USE.md, Step 6):
      - `invocation.binary` — absolute path to the executable
      - `invocation.positional_layout` — schema keys that map to positional args
      - `inputSchema.properties[*].flags` — flag aliases for the argument
      - `inputSchema.properties[*].type` — boolean / array / string / number
    """

    def __init__(self, loader: CatalogRuntimeLoader, default_timeout_seconds: int = 20, max_output_chars: int = 12000):
        self.loader = loader
        self.default_timeout_seconds = default_timeout_seconds
        self.max_output_chars = max_output_chars

    def run(
        self,
        tool_record: dict[str, Any],
        args: dict[str, Any] | None = None,
        positional: list[str] | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        args = args or {}
        positional = positional or []

        manifest = self.loader.load_manifest(
            catalog_path=tool_record["catalog_path"],
            group=tool_record["group"],
            tier=tool_record["tier"],
            name=tool_record["name"],
        )

        argv = self._build_argv(manifest, args, positional)

        started = time.perf_counter()
        timeout_used = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_used,
                check=False,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "tool": tool_record["name"],
                "executable": tool_record["executable"],
                "argv": argv,
                "exit_code": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "timed_out": False,
                "stdout": self._clip(proc.stdout),
                "stderr": self._clip(proc.stderr),
            }
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "tool": tool_record["name"],
                "executable": tool_record["executable"],
                "argv": argv,
                "exit_code": 124,
                "elapsed_ms": elapsed_ms,
                "timed_out": True,
                "stdout": self._clip(exc.stdout or ""),
                "stderr": self._clip(exc.stderr or "") or f"Timed out after {timeout_used} seconds",
            }
        except FileNotFoundError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "tool": tool_record["name"],
                "executable": tool_record["executable"],
                "argv": argv,
                "exit_code": 127,
                "elapsed_ms": elapsed_ms,
                "timed_out": False,
                "stdout": "",
                "stderr": str(exc),
            }

    def _build_argv(self, manifest: dict[str, Any], args: dict[str, Any], positional: list[str]) -> list[str]:
        invocation = manifest.get("invocation", {})
        schema = manifest.get("inputSchema", {})
        properties = schema.get("properties", {})
        additional_props = bool(schema.get("additionalProperties", True))

        argv = [invocation.get("binary", manifest.get("executable", manifest["name"]))]
        consumed_for_flags: set[str] = set()

        for key, value in args.items():
            if key not in properties:
                if additional_props:
                    continue
                raise ValueError(f"Unknown argument '{key}' for tool '{manifest['name']}'")

            if value is None:
                continue

            prop = properties[key]
            flags = prop.get("flags", [])
            if not flags:
                continue

            flag = self._preferred_flag(flags)
            arg_type = prop.get("type", "string")

            if arg_type == "boolean":
                if bool(value):
                    argv.append(flag)
                consumed_for_flags.add(key)
                continue

            if arg_type == "array":
                if not isinstance(value, list):
                    raise ValueError(f"Argument '{key}' must be a list")
                for item in value:
                    argv.extend([flag, str(item)])
                consumed_for_flags.add(key)
                continue

            argv.extend([flag, str(value)])
            consumed_for_flags.add(key)

        for key in invocation.get("positional_layout", []):
            if key in args and key not in consumed_for_flags and args[key] is not None:
                argv.append(str(args[key]))

        argv.extend(str(item) for item in positional)
        return argv

    @staticmethod
    def _preferred_flag(flags: list[str]) -> str:
        long_flags = [f for f in flags if f.startswith("--")]
        return long_flags[-1] if long_flags else flags[0]

    def _clip(self, text: str) -> str:
        if len(text) <= self.max_output_chars:
            return text
        return text[: self.max_output_chars] + "\n...[truncated]"
