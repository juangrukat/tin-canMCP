# SSE Transport

SSE mode exposes tin-canMCP over HTTP with server-sent events.

## Run

```bash
python main.py --transport=sse
```

Alias:

```bash
python main.py --transport=web
```

Or with environment variable:

```bash
MCP_TRANSPORT=sse python main.py
```

## Notes

- Default bind address/port come from the MCP runtime defaults unless overridden by your environment.
- Use this mode for browser or remote HTTP-based integrations.
