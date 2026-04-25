# Contributing

Contributions are welcome for improving tin-canMCP.

## Development Setup

```bash
./dev-setup.sh
```

Or manually:

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Code Guidelines

- Target Python 3.11+.
- Keep the broker runtime (`app/catalog_runtime/`) and broker tool registrations (`app/tools/catalog_tools.py`) generic. Domain-specific logic belongs in `catalog-runtime/` as JSON, not Python.
- Prefer clear typing and explicit error handling.
- Update `HOW-TO-USE.md` and `docs/catalog-runtime-template.md` when behavior changes.

## Project Structure

- `app/catalog_runtime/`: broker, loader, and executor (runtime — avoid modifying)
- `app/tools/`: registers the 7 broker MCP tools (avoid modifying; do not add domain @mcp.tool() entries here)
- `app/prompts/`: optional MCP prompt registrations
- `app/config.py`: environment-backed settings
- `main.py`: startup and transport selection
- `catalog-runtime/registry/`: catalog authored as JSON (this is what downstream users edit)
- `catalog-runtime/schema/`: JSON Schemas for registry files
- `scripts/`: scaffolder and validator
- `ai-prompts/`: AI implementation prompt + source hints
- `docs/`: schema contract and transport notes

## Validation

```bash
python -m compileall app scripts main.py
python scripts/validate_registry.py catalog-runtime
python main.py --help
```

## Pull Requests

- Keep each PR focused.
- Describe the change and the reason.
- Include validation steps and results.
