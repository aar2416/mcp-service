"""Escape hatch for any Zendesk endpoint without a dedicated tool."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def zendesk_api_request(
        method: str,
        path: str,
        params: Json | None = None,
        body: Any = None,
    ) -> Any:
        """Call any Zendesk REST endpoint under /api/v2 directly.

        method: GET|POST|PUT|PATCH|DELETE. path is relative to /api/v2, e.g. '/tickets/123.json'
        or '/help_center/en-us/articles.json'. `params` are query-string values, `body` the JSON
        payload. Honors ZENDESK_READ_ONLY. Prefer the dedicated tools when one exists."""
        if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Unsupported method")
        if not path.startswith("/"):
            raise ValueError("path must start with '/' and be relative to /api/v2")
        return await get_client().request(method, path, params=params, json=body)

    @mcp.tool()
    async def follow_next_page(next_page_url: str) -> Any:
        """Fetch the `next_page` URL returned by a previous list call (same Zendesk account only)."""
        return await get_client().get(next_page_url)
