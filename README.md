# ollagraph-mcp

MCP (Model Context Protocol) server exposing [ollagraph.com](https://ollagraph.com)'s 132-endpoint web-automation + intelligence API as tools for any MCP-compatible client (OpenFang agents, Claude Desktop, Continue.dev, etc.).

## Why this exists

ollagraph runs the web-automation infrastructure powering OllaSuper:
- 200M+ owned proxies (residential, datacenter, mobile, ISP)
- Native scraping, structured extraction, AEO/SEO audits, intelligence layer (DNS / WHOIS / cert transparency / etc.)
- Direct egress to Apify + Bright Data networks for the long-tail 10%

This MCP server makes those tools available to any AI agent without each project re-implementing the HTTP plumbing, auth, error mapping, and tool schema definition.

## Install

```bash
npm install
npm run build
```

## Run

```bash
OLLAGRAPH_API_KEY=osk_... node dist/server.js
```

The server speaks MCP over stdio.

## Tools shipped in v0.1 (8 of 132 endpoints)

- `ollagraph_scrape` — clean-markdown scrape of a URL via ollagraph proxies
- `ollagraph_aeo_page_audit` — real Answer-Engine-Optimization audit, returns score + breakdowns
- `ollagraph_aeo_citation_readiness` — citation-readiness score for AI search engines
- `ollagraph_seo_keyword_extract` — keyword frequencies extracted from a URL
- `ollagraph_extract_structured` — JSON-LD + OpenGraph + Twitter + microdata + RDFa
- `ollagraph_intel_whois` — live WHOIS for a domain
- `ollagraph_intel_ssl` — TLS cert analysis
- `ollagraph_convert_html_to_markdown` — clean HTML → markdown

The remaining ~124 endpoints will land in v0.2 via OpenAPI-driven generation.

## Register in OpenFang

Add to your openfang config.toml:

```toml
[[mcp_servers]]
name = "ollagraph"
timeout_secs = 60
env = ["OLLAGRAPH_API_KEY"]

[mcp_servers.transport]
type = "stdio"
command = "node"
args = ["/path/to/ollagraph-mcp/dist/server.js"]
```

Then `systemctl restart openfang.service`. Tools appear as `mcp_ollagraph_<name>`.

## Register in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "ollagraph": {
      "command": "node",
      "args": ["/path/to/ollagraph-mcp/dist/server.js"],
      "env": { "OLLAGRAPH_API_KEY": "osk_..." }
    }
  }
}
```

## License

MIT.
