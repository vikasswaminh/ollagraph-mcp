# Ollagraph MCP server

An MCP server that exposes the full Ollagraph API (212 endpoints across fetch,
extract, audit, intelligence, and AEO/SEO) as tools your AI agent can call directly.

Works with Claude Desktop, Cursor, Cline, Continue, and any other MCP-capable
client. Built on [FastMCP](https://github.com/jlowin/fastmcp) — the server is a
thin wrapper around our published OpenAPI spec, so every endpoint stays in lockstep
with the API.

## Quick start

```bash
# Get an API key from https://ollagraph.com/signup (free, 1,000 credits)
export OLLAGRAPH_API_KEY="osk_..."

# Run the server
pipx run ollagraph-mcp
# or
pip install ollagraph-mcp && ollagraph-mcp
```

## Use with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "ollagraph": {
      "command": "pipx",
      "args": ["run", "ollagraph-mcp"],
      "env": {
        "OLLAGRAPH_API_KEY": "osk_..."
      }
    }
  }
}
```

Restart Claude Desktop. The tools (`scrape`, `extract_clean`, `aeo_page_audit`,
etc.) appear in the tool list.

## Use with Cursor / Cline / Continue

Same config shape. Each client has its own MCP config location; see their docs.

## Use with the MCP Inspector

```bash
npx @modelcontextprotocol/inspector pipx run ollagraph-mcp
```

Opens the Inspector UI for poking the tools directly.

## What this gives you

- 212 tools, one per Ollagraph endpoint, auto-generated from our OpenAPI spec
  (the catalog tracks the live API — restart to pick up newly shipped endpoints)
- Tool descriptions pulled from operation summaries — the LLM reads them to
  decide which to call
- Bearer auth handled for you; just set `OLLAGRAPH_API_KEY` once
- Stays in sync with the API: when we ship a new endpoint, restart the server
  and your agent gets the new tool

## Configuration

| Env var | Default | Description |
| --- | --- | --- |
| `OLLAGRAPH_API_KEY` | _(required)_ | Bearer token from your Ollagraph account |
| `OLLAGRAPH_API_URL` | `https://api.ollagraph.com` | Override for self-hosted deployments |
| `OLLAGRAPH_TIMEOUT_SECONDS` | `60` | Per-tool-call HTTP timeout |

## License

MIT.
