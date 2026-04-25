# STDIO Transport

STDIO is the default transport for tin-canMCP. It is the best choice for local integrations where a client launches the MCP server as a subprocess.

## Run

```bash
python main.py --transport=stdio
```

Or with environment variable:

```bash
MCP_TRANSPORT=stdio python main.py
```

## Typical Client Config

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["main.py", "--transport=stdio"]
    }
  }
}
```

## Notes

- STDIO does not expose a network port.
- Use this mode for local and CI-friendly execution.
