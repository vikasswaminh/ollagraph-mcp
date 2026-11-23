"""
Ollagraph MCP server.

Loads the Ollagraph OpenAPI spec and exposes every endpoint as an MCP tool.
The whole server is roughly 30 lines of glue because FastMCP does the heavy
lifting — it reads operation summaries, request schemas, and parameter types
straight from the spec.

Auth: a single Bearer token (`OLLAGRAPH_API_KEY`) is attached to every outbound
request. The user's MCP client never sees it.

Sync model: stdio transport by default (which is what Claude Desktop, Cursor,
and Cline use). Override with `--transport http` for a hosted MCP scenario.
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx
from fastmcp import FastMCP

from .naming import build_mcp_names


DEFAULT_API_URL = "https://api.ollagraph.com"
DEFAULT_TIMEOUT_SECONDS = 60


def build_server(
    *,
    api_url: str,
    api_key: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> FastMCP:
    """Construct an MCP server backed by the live Ollagraph OpenAPI spec.

    Reads the spec on startup, so the catalog of MCP tools always matches what
    the API actually serves. When the API ships a new endpoint, restart this
    server and your agent gets the new tool.
    """
    # We talk to api.ollagraph.com for the spec AND for tool invocations.
    # Same client, same auth header — FastMCP wires the spec's `securitySchemes`
    # to whichever HTTP client we pass in.
    client = httpx.AsyncClient(
        base_url=api_url,
        timeout=timeout_seconds,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ollagraph-mcp/0.1.1",
        },
    )

    # Pull the spec live. If the API is unreachable, fail loudly — the user
    # would otherwise see "no tools" and have no idea why.
    spec_url = f"{api_url.rstrip('/')}/openapi.json"
    try:
        spec = httpx.get(spec_url, timeout=15.0).json()
    except Exception as exc:  # noqa: BLE001 — we want the full message
        raise SystemExit(
            f"ollagraph-mcp: cannot fetch OpenAPI spec from {spec_url}: {exc}\n"
            f"Check OLLAGRAPH_API_URL and your network."
        ) from exc

    # Auto-derived clean tool names from URL paths.
    # Without this, FastMCP names tools after the spec's operationId
    # ('scrape_endpoint_v1_scrape_post'), which is functional but noisy.
    # build_mcp_names() collapses those into 'scrape', 'aeo_page_audit', etc.
    mcp_names = build_mcp_names(spec)

    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="ollagraph",
        mcp_names=mcp_names,
    )
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ollagraph-mcp",
        description="Run the Ollagraph MCP server (stdio by default).",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport. Use stdio for Claude Desktop / Cursor / Cline.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP transport bind host (only used with --transport http).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="HTTP transport bind port (only used with --transport http).",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OLLAGRAPH_API_KEY", "").strip()
    if not api_key:
        sys.stderr.write(
            "ollagraph-mcp: OLLAGRAPH_API_KEY is not set.\n"
            "Get a key at https://ollagraph.com/signup and export it:\n"
            "  export OLLAGRAPH_API_KEY=osk_...\n"
        )
        sys.exit(2)

    api_url = os.environ.get("OLLAGRAPH_API_URL", DEFAULT_API_URL).rstrip("/")
    timeout = int(os.environ.get("OLLAGRAPH_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))

    mcp = build_server(api_url=api_url, api_key=api_key, timeout_seconds=timeout)

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
