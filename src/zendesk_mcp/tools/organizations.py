"""Organizations."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def _clean(d: Json) -> Json:
    return {k: v for k, v in d.items() if v is not None}


def _ids(ids: list[int]) -> str:
    return ",".join(str(i) for i in ids)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_organizations(page_size: int = 100, max_pages: int = 1, page: int | None = None) -> Json:
        return await get_client().list(
            "/organizations.json", "organizations", page_size=page_size, max_pages=max_pages, page=page
        )

    @mcp.tool()
    async def get_organization(organization_id: int) -> Json:
        return await get_client().get(f"/organizations/{organization_id}.json")

    @mcp.tool()
    async def get_many_organizations(organization_ids: list[int]) -> Json:
        return await get_client().get("/organizations/show_many.json", {"ids": _ids(organization_ids)})

    @mcp.tool()
    async def count_organizations() -> Json:
        return await get_client().get("/organizations/count.json")

    @mcp.tool()
    async def search_organizations(
        name: str | None = None, external_id: str | None = None
    ) -> Json:
        """Exact-name or external_id lookup. For fuzzy search use `search` with 'type:organization'."""
        return await get_client().get(
            "/organizations/search.json", {"name": name, "external_id": external_id}
        )

    @mcp.tool()
    async def autocomplete_organizations(name: str) -> Json:
        return await get_client().get("/organizations/autocomplete.json", {"name": name})

    @mcp.tool()
    async def create_organization(
        name: str,
        domain_names: list[str] | None = None,
        details: str | None = None,
        notes: str | None = None,
        group_id: int | None = None,
        shared_tickets: bool | None = None,
        shared_comments: bool | None = None,
        external_id: str | None = None,
        tags: list[str] | None = None,
        organization_fields: Json | None = None,
    ) -> Json:
        org = _clean({
            "name": name, "domain_names": domain_names, "details": details, "notes": notes,
            "group_id": group_id, "shared_tickets": shared_tickets,
            "shared_comments": shared_comments, "external_id": external_id, "tags": tags,
            "organization_fields": organization_fields,
        })
        return await get_client().post("/organizations.json", {"organization": org})

    @mcp.tool()
    async def create_or_update_organization(organization: Json) -> Json:
        """Upsert by id/external_id/name. `organization` is an organization object."""
        return await get_client().post(
            "/organizations/create_or_update.json", {"organization": organization}
        )

    @mcp.tool()
    async def create_many_organizations(organizations: list[Json]) -> Json:
        return await get_client().post("/organizations/create_many.json", {"organizations": organizations})

    @mcp.tool()
    async def update_organization(organization_id: int, fields: Json) -> Json:
        """Update an organization, e.g. {"notes":"VIP","domain_names":["acme.com"]}."""
        return await get_client().put(f"/organizations/{organization_id}.json", {"organization": fields})

    @mcp.tool()
    async def update_many_organizations(organization_ids: list[int], fields: Json) -> Json:
        return await get_client().put(
            "/organizations/update_many.json", {"organization": fields},
            params={"ids": _ids(organization_ids)},
        )

    @mcp.tool()
    async def delete_organization(organization_id: int) -> Json:
        return await get_client().delete(f"/organizations/{organization_id}.json")

    @mcp.tool()
    async def delete_many_organizations(organization_ids: list[int]) -> Json:
        return await get_client().delete(
            "/organizations/destroy_many.json", params={"ids": _ids(organization_ids)}
        )

    @mcp.tool()
    async def get_organization_related_info(organization_id: int) -> Json:
        return await get_client().get(f"/organizations/{organization_id}/related.json")

    @mcp.tool()
    async def list_organization_users(organization_id: int, page_size: int = 100, max_pages: int = 1) -> Json:
        return await get_client().list(
            f"/organizations/{organization_id}/users.json", "users",
            page_size=page_size, max_pages=max_pages,
        )

    @mcp.tool()
    async def list_organization_tags(organization_id: int) -> Json:
        return await get_client().get(f"/organizations/{organization_id}/tags.json")

    @mcp.tool()
    async def add_organization_tags(organization_id: int, tags: list[str]) -> Json:
        return await get_client().put(f"/organizations/{organization_id}/tags.json", {"tags": tags})

    @mcp.tool()
    async def remove_organization_tags(organization_id: int, tags: list[str]) -> Json:
        return await get_client().delete(f"/organizations/{organization_id}/tags.json", body={"tags": tags})

    @mcp.tool()
    async def list_organization_subscriptions(organization_id: int | None = None) -> Json:
        """Who is subscribed (CC'd) to an organization's tickets."""
        path = (
            f"/organizations/{organization_id}/subscriptions.json"
            if organization_id else "/organization_subscriptions.json"
        )
        return await get_client().list(path, "organization_subscriptions")
