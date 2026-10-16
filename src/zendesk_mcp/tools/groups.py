"""Groups and group memberships (agent assignment)."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_groups(assignable_only: bool = False, user_id: int | None = None) -> Json:
        """List groups. assignable_only=True returns only groups tickets can be assigned to;
        user_id lists the groups a given agent belongs to."""
        if user_id:
            path = f"/users/{user_id}/groups.json"
        elif assignable_only:
            path = "/groups/assignable.json"
        else:
            path = "/groups.json"
        return await get_client().list(path, "groups")

    @mcp.tool()
    async def get_group(group_id: int) -> Json:
        return await get_client().get(f"/groups/{group_id}.json")

    @mcp.tool()
    async def count_groups() -> Json:
        return await get_client().get("/groups/count.json")

    @mcp.tool()
    async def create_group(name: str, description: str | None = None) -> Json:
        group = {"name": name}
        if description:
            group["description"] = description
        return await get_client().post("/groups.json", {"group": group})

    @mcp.tool()
    async def update_group(group_id: int, fields: Json) -> Json:
        return await get_client().put(f"/groups/{group_id}.json", {"group": fields})

    @mcp.tool()
    async def delete_group(group_id: int) -> Json:
        return await get_client().delete(f"/groups/{group_id}.json")

    @mcp.tool()
    async def list_group_memberships(
        group_id: int | None = None, user_id: int | None = None, assignable_only: bool = False
    ) -> Json:
        """Which agents are in which groups (filter by group or user)."""
        if group_id:
            path = f"/groups/{group_id}/memberships.json"
        elif user_id:
            path = f"/users/{user_id}/group_memberships.json"
        elif assignable_only:
            path = "/group_memberships/assignable.json"
        else:
            path = "/group_memberships.json"
        return await get_client().list(path, "group_memberships")

    @mcp.tool()
    async def add_agent_to_group(user_id: int, group_id: int, default: bool | None = None) -> Json:
        m: Json = {"user_id": user_id, "group_id": group_id}
        if default is not None:
            m["default"] = default
        return await get_client().post("/group_memberships.json", {"group_membership": m})

    @mcp.tool()
    async def remove_agent_from_group(membership_id: int) -> Json:
        return await get_client().delete(f"/group_memberships/{membership_id}.json")

    @mcp.tool()
    async def make_group_membership_default(user_id: int, membership_id: int) -> Json:
        return await get_client().put(
            f"/users/{user_id}/group_memberships/{membership_id}/make_default.json"
        )
