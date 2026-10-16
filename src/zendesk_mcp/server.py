from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .config import Settings
from .tools import register_all

INSTRUCTIONS = (
    "Tools for the Zendesk Support and Help Center APIs. List tools return "
    "{count, <items>, has_more, next_page}; pass `page`/`max_pages` or call `follow_next_page` "
    "to continue. Bulk operations return a job_status - poll with `get_job_status`. "
    "Destructive tools (delete_*, permanently_delete_*, redact_*) cannot be undone or are hard "
    "to undo: confirm with the user first. For anything not covered, use `zendesk_api_request`."
)


def create_server(
    host: str = "127.0.0.1", port: int = 8000, toolsets: list[str] | None = None
) -> FastMCP:
    mcp = FastMCP("zendesk", instructions=INSTRUCTIONS, host=host, port=port)
    register_all(mcp, toolsets)
    return mcp


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), stream=sys.stderr)
    try:
        settings = Settings.from_env()  # fail fast on bad config
    except RuntimeError as exc:
        sys.exit(f"Configuration error: {exc}")

    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        sys.exit("MCP_TRANSPORT must be stdio, sse or streamable-http")

    mcp = create_server(
        host=os.environ.get("MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("MCP_PORT", "8000")),
        toolsets=[t.strip() for t in os.environ.get("ZENDESK_TOOLSETS", "").split(",") if t.strip()]
        or None,
    )
    logging.getLogger(__name__).info(
        "Zendesk MCP -> %s (transport=%s, read_only=%s)",
        settings.base_url, transport, settings.read_only,
    )
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
