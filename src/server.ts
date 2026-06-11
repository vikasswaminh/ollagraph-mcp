#!/usr/bin/env node
/**
 * OllaGraph MCP Server v0.1
 *
 * Exposes a curated subset of ollagraph.com endpoints as MCP tools,
 * usable by OpenFang agents, Claude Desktop, or any MCP client.
 *
 * Auth via OLLAGRAPH_API_KEY env var. Transport: stdio.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const OLLAGRAPH_BASE = "https://api.ollagraph.com";
const API_KEY = process.env.OLLAGRAPH_API_KEY;

if (!API_KEY) {
  console.error("FATAL: OLLAGRAPH_API_KEY env var is required");
  process.exit(1);
}

type ToolDef = {
  name: string;
  description: string;
  inputSchema: { type: "object"; properties: Record<string, any>; required?: string[] };
  endpoint: string;
  buildBody: (args: Record<string, any>) => Record<string, any>;
};

const tools: ToolDef[] = [
  {
    name: "scrape",
    description: "Fetch a single URL via ollagraph (200M owned proxies + stealth headers). Returns clean markdown extracted from the page. Use for research, content analysis, competitor scraping.",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "Absolute http(s) URL to fetch" },
        stealth: { type: "boolean", description: "Use stealth + residential proxies (default true)" },
      },
      required: ["url"],
    },
    endpoint: "/v1/scrape",
    buildBody: (a) => ({ url: a.url, format: "markdown", stealth: a.stealth !== false }),
  },
  {
    name: "aeo_page_audit",
    description: "Run a real AEO (Answer Engine Optimization) audit on a URL. Returns overall_score (0-100), grade letter, and breakdowns of how likely the page is to be cited by ChatGPT, Claude, Perplexity, and other AI engines.",
    inputSchema: {
      type: "object",
      properties: { url: { type: "string", description: "Absolute http(s) URL to audit" } },
      required: ["url"],
    },
    endpoint: "/v1/aeo/page-audit",
    buildBody: (a) => ({ url: a.url }),
  },
  {
    name: "aeo_citation_readiness",
    description: "Citation-readiness score for AI search. Faster than the full page audit; focuses on structural signals AI crawlers look for. Returns score + specific blockers.",
    inputSchema: {
      type: "object",
      properties: { url: { type: "string", description: "Absolute http(s) URL" } },
      required: ["url"],
    },
    endpoint: "/v1/aeo/citation-readiness",
    buildBody: (a) => ({ url: a.url }),
  },
  {
    name: "seo_keyword_extract",
    description: "Extract weighted keyword list from a URL content. Returns ranked words with frequencies. Use for content briefs, competitor keyword analysis, identifying what a page actually ranks for.",
    inputSchema: {
      type: "object",
      properties: { url: { type: "string", description: "Absolute http(s) URL" } },
      required: ["url"],
    },
    endpoint: "/v1/seo/keyword-extract",
    buildBody: (a) => ({ url: a.url }),
  },
  {
    name: "extract_structured",
    description: "Pull all structured data from a URL: JSON-LD, microdata, OpenGraph, Twitter Card, RDFa, meta tags. Returns a normalized JSON object. Use for competitor schema audits and company-page enrichment.",
    inputSchema: {
      type: "object",
      properties: { url: { type: "string", description: "Absolute http(s) URL" } },
      required: ["url"],
    },
    endpoint: "/v1/extract/structured",
    buildBody: (a) => ({ url: a.url }),
  },
  {
    name: "intel_whois",
    description: "Live WHOIS lookup for a domain. Returns registrar, dates, contacts, name servers. Use for domain ownership research, security audits, M&A due diligence.",
    inputSchema: {
      type: "object",
      properties: { domain: { type: "string", description: "Bare domain like example.com" } },
      required: ["domain"],
    },
    endpoint: "/v1/intel/whois",
    buildBody: (a) => ({ domain: a.domain }),
  },
  {
    name: "intel_ssl",
    description: "TLS certificate analysis for a domain. Returns issuer, validity dates, key size, SAN list, ciphers. Use for security audits, SOC 2 evidence, certificate expiry monitoring.",
    inputSchema: {
      type: "object",
      properties: { domain: { type: "string", description: "Bare domain like example.com" } },
      required: ["domain"],
    },
    endpoint: "/v1/intel/ssl",
    buildBody: (a) => ({ domain: a.domain }),
  },
  {
    name: "convert_html_to_markdown",
    description: "Convert a chunk of HTML into clean markdown. Use when you already have HTML and want a clean reading version. For URLs, prefer ollagraph_scrape instead.",
    inputSchema: {
      type: "object",
      properties: { html: { type: "string", description: "Raw HTML string. Can be full document or fragment." } },
      required: ["html"],
    },
    endpoint: "/v1/convert/html-to-markdown",
    buildBody: (a) => ({ html: a.html }),
  },
];

async function dispatch(tool: ToolDef, args: Record<string, any>): Promise<unknown> {
  const body = tool.buildBody(args);
  const start = Date.now();
  const res = await fetch(`${OLLAGRAPH_BASE}${tool.endpoint}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const ms = Date.now() - start;
  console.error(`[ollagraph-mcp] ${tool.name} ${tool.endpoint} HTTP ${res.status} in ${ms}ms bytes=${text.length}`);
  if (!res.ok) {
    throw new Error(`ollagraph ${tool.endpoint} returned HTTP ${res.status}: ${text.slice(0, 300)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

const server = new Server(
  { name: "ollagraph", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: tools.map((t) => ({
    name: t.name,
    description: t.description,
    inputSchema: t.inputSchema,
  })),
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  const tool = tools.find((t) => t.name === name);
  if (!tool) {
    return { isError: true, content: [{ type: "text", text: `Unknown tool: ${name}` }] };
  }
  try {
    const result = await dispatch(tool, args);
    return {
      content: [
        {
          type: "text",
          text: typeof result === "string" ? result : JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { isError: true, content: [{ type: "text", text: msg }] };
  }
});

const transport = new StdioServerTransport();
server.connect(transport).then(
  () => console.error("[ollagraph-mcp] connected on stdio"),
  (err) => {
    console.error("[ollagraph-mcp] failed to connect:", err);
    process.exit(1);
  }
);
