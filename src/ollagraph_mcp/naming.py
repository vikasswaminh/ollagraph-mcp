"""
Tool-name normalization.

FastMCP auto-derives MCP tool names from OpenAPI ``operationId`` fields, which
in our spec look like ``scrape_endpoint_v1_scrape_post`` — readable but ugly,
and an LLM picking tools from a long list reads worse names slower.

This module derives a short, predictable name from the URL path + HTTP method,
and returns a ``{operationId: clean_name}`` mapping that FastMCP applies during
spec parsing.

Examples (path, method) -> name:
    POST /v1/scrape                    -> scrape
    POST /v1/scrape/batch              -> scrape_batch
    POST /v1/scrape/batch/async        -> scrape_batch_async
    GET  /v1/jobs/{job_id}             -> jobs_get
    POST /v1/aeo/page-audit            -> aeo_page_audit
    POST /v1/seo/snippet-candidates    -> seo_snippet_candidates
    POST /v1/convert/pdf-to-markdown   -> convert_pdf_to_markdown
    POST /v1/intel/geoip/bulk          -> intel_geoip_bulk
    DELETE /v1/keys/{key_id}           -> keys_delete

We deliberately do NOT include the HTTP method in the prefix for POST (the
common case) because every endpoint that takes a request body is POST and
the prefix would be noise. GET, DELETE, PUT get a ``_get`` / ``_delete`` /
``_put`` suffix so the LLM can disambiguate.
"""
from __future__ import annotations

import re
from typing import Any


_PATH_PARAM_RE = re.compile(r"\{[^}]+\}")
_NONWORD_RE = re.compile(r"[^a-z0-9]+")


def derive_tool_name(path: str, method: str) -> str:
    """Derive a clean MCP tool name from (path, method).

    The result is lowercase, snake-case, prefix-free of '/v1', and free of
    path parameters. Reserved words are not handled — we trust the API not
    to name an endpoint after a Python keyword.
    """
    p = path.lower()
    # Strip the API version prefix; if we ever move to /v2 we'd want both
    # versions to deconflict, but for now there is one version.
    if p.startswith("/v1/"):
        p = p[len("/v1/"):]
    elif p.startswith("/"):
        p = p[1:]

    # Drop path parameters ({job_id}, {key_id}) — they collapse to an
    # empty segment which we then dedupe.
    p = _PATH_PARAM_RE.sub("", p)

    # Normalize all separators (hyphen, slash, dot) to underscore.
    p = _NONWORD_RE.sub("_", p)
    p = re.sub(r"_+", "_", p).strip("_")

    m = method.lower()
    if m == "post" or not p:
        return p or "root"
    # For non-POST verbs, append the verb so the LLM can tell them apart
    # from a POST at the same path.
    return f"{p}_{m}"


def build_mcp_names(openapi_spec: dict[str, Any]) -> dict[str, str]:
    """Build a {operationId: clean_name} map from the spec.

    Operations without an operationId are skipped (FastMCP synthesizes one
    in that case, and we don't try to fight the synthesized name).

    Collisions are detected and resolved by suffixing ``_2``, ``_3``, ...
    so the result is always unique. Collisions shouldn't happen with our
    spec today but the guard means we won't silently drop tools later.
    """
    seen: dict[str, int] = {}
    out: dict[str, str] = {}
    for path, ops in (openapi_spec.get("paths") or {}).items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            op_id = (op or {}).get("operationId") if isinstance(op, dict) else None
            if not op_id:
                continue
            base = derive_tool_name(path, method)
            count = seen.get(base, 0)
            seen[base] = count + 1
            out[op_id] = base if count == 0 else f"{base}_{count + 1}"
    return out
