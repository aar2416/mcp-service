"""Zendesk search (tickets, users, orgs, articles) and incremental exports."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search(
        query: str,
        sort_by: str | None = None,
        sort_order: str | None = None,
        include: str | None = None,
        page_size: int = 100,
        max_pages: int = 1,
        page: int | None = None,
    ) -> Json:
        """Search tickets, users, organizations and groups. Syntax examples:
        'type:ticket status:open priority:high assignee:me', 'created>2024-01-01 tags:vip',
        'requester:jane@acme.com', 'organization:"Acme"', 'status<solved'; bare words match
        subject/description/comments. Max 1000 results; use `export_search` for more."""
        return await get_client().list(
            "/search.json", "results", page_size=page_size, max_pages=max_pages, page=page,
            params={"query": query, "sort_by": sort_by, "sort_order": sort_order, "include": include},
        )

    @mcp.tool()
    async def search_tickets(
        query: str = "",
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        requester: str | None = None,
        tags: list[str] | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        updated_after: str | None = None,
        sort_by: str | None = "updated_at",
        sort_order: str | None = "desc",
        page_size: int = 100,
        max_pages: int = 1,
    ) -> Json:
        """Convenience ticket search. Builds a 'type:ticket ...' query from the filters and any
        free-text/raw `query`. Dates are YYYY-MM-DD. assignee/requester: email, name or 'me'."""
        parts = ["type:ticket"]
        if status:
            parts.append(f"status:{status}")
        if priority:
            parts.append(f"priority:{priority}")
        if assignee:
            parts.append(f'assignee:"{assignee}"' if " " in assignee else f"assignee:{assignee}")
        if requester:
            parts.append(f'requester:"{requester}"' if " " in requester else f"requester:{requester}")
        for t in tags or []:
            parts.append(f"tags:{t}")
        if created_after:
            parts.append(f"created>{created_after}")
        if created_before:
            parts.append(f"created<{created_before}")
        if updated_after:
            parts.append(f"updated>{updated_after}")
        if query:
            parts.append(query)
        return await get_client().list(
            "/search.json", "results", page_size=page_size, max_pages=max_pages,
            params={"query": " ".join(parts), "sort_by": sort_by, "sort_order": sort_order},
        )

    @mcp.tool()
    async def search_count(query: str) -> Json:
        """Number of results a search query would return."""
        return await get_client().get("/search/count.json", {"query": query})

    @mcp.tool()
    async def export_search(
        query: str,
        object_type: str = "ticket",
        page_size: int = 100,
        after_cursor: str | None = None,
    ) -> Json:
        """Cursor-based search export without the 1000-result cap. object_type:
        ticket|organization|user|group. Pass the previous `meta.after_cursor` to continue."""
        return await get_client().get(
            "/search/export.json",
            {"query": query, "filter[type]": object_type, "page[size]": min(page_size, 1000),
             "page[after]": after_cursor},
        )

    # ---------------------------------------------------- incremental exports
    @mcp.tool()
    async def incremental_export(
        resource: str,
        start_time: int | None = None,
        cursor: str | None = None,
        per_page: int = 1000,
        include: str | None = None,
    ) -> Json:
        """Cursor-based incremental export. resource: tickets | users | organizations |
        ticket_events | ticket_metric_events. First call needs start_time (unix epoch);
        subsequent calls pass `after_cursor` as cursor. Stop when end_of_stream is true."""
        allowed = {"tickets", "users", "organizations", "ticket_events", "ticket_metric_events"}
        if resource not in allowed:
            raise ValueError(f"resource must be one of {sorted(allowed)}")
        path = {
            "tickets": "/incremental/tickets/cursor.json",
            "users": "/incremental/users/cursor.json",
            "organizations": "/incremental/organizations.json",
            "ticket_events": "/incremental/ticket_events.json",
            "ticket_metric_events": "/incremental/ticket_metric_events.json",
        }[resource]
        params: Json = {"per_page": per_page, "include": include}
        if cursor:
            params["cursor"] = cursor
        else:
            params["start_time"] = start_time
        return await get_client().get(path, params)
