"""Users, identities, and related records."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def _clean(d: Json) -> Json:
    return {k: v for k, v in d.items() if v is not None}


def _ids(ids: list[int]) -> str:
    return ",".join(str(i) for i in ids)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_users(
        role: str | None = None, permission_set: int | None = None,
        page_size: int = 100, max_pages: int = 1, page: int | None = None,
    ) -> Json:
        """List users. role: end-user | agent | admin."""
        return await get_client().list(
            "/users.json", "users", page_size=page_size, max_pages=max_pages, page=page,
            params={"role": role, "permission_set": permission_set},
        )

    @mcp.tool()
    async def get_user(user_id: int, include: str | None = None) -> Json:
        """Get a user. include e.g. 'organizations,groups,roles'."""
        return await get_client().get(f"/users/{user_id}.json", {"include": include})

    @mcp.tool()
    async def get_current_user() -> Json:
        """The authenticated user (whoami) - handy to verify credentials."""
        return await get_client().get("/users/me.json")

    @mcp.tool()
    async def get_many_users(user_ids: list[int]) -> Json:
        return await get_client().get("/users/show_many.json", {"ids": _ids(user_ids)})

    @mcp.tool()
    async def count_users() -> Json:
        return await get_client().get("/users/count.json")

    @mcp.tool()
    async def search_users(query: str, page_size: int = 100, max_pages: int = 1) -> Json:
        """Find users by name, email, phone, external_id or other searchable field."""
        return await get_client().list(
            "/users/search.json", "users", params={"query": query},
            page_size=page_size, max_pages=max_pages,
        )

    @mcp.tool()
    async def autocomplete_users(name: str) -> Json:
        """Prefix match on user name."""
        return await get_client().get("/users/autocomplete.json", {"name": name})

    @mcp.tool()
    async def create_user(
        name: str,
        email: str | None = None,
        role: str | None = None,
        organization_id: int | None = None,
        phone: str | None = None,
        external_id: str | None = None,
        tags: list[str] | None = None,
        verified: bool | None = None,
        skip_verify_email: bool | None = None,
        user_fields: Json | None = None,
        extra: Json | None = None,
    ) -> Json:
        """Create a user (end-user by default). role: end-user|agent|admin. `extra` merges any
        other user attribute (custom_role_id, locale, time_zone, notes, details...)."""
        user = _clean({
            "name": name, "email": email, "role": role, "organization_id": organization_id,
            "phone": phone, "external_id": external_id, "tags": tags, "verified": verified,
            "skip_verify_email": skip_verify_email, "user_fields": user_fields,
        })
        user.update(extra or {})
        return await get_client().post("/users.json", {"user": user})

    @mcp.tool()
    async def create_or_update_user(user: Json) -> Json:
        """Upsert by email or external_id. `user` is a user object, e.g.
        {"name": "Jane", "email": "jane@acme.com"}."""
        return await get_client().post("/users/create_or_update.json", {"user": user})

    @mcp.tool()
    async def create_many_users(users: list[Json]) -> Json:
        """Bulk create up to 100 users. Returns a job_status."""
        return await get_client().post("/users/create_many.json", {"users": users})

    @mcp.tool()
    async def update_user(user_id: int, fields: Json) -> Json:
        """Update a user. `fields` e.g. {"role":"agent","organization_id":1,"tags":["vip"],
        "user_fields":{"plan":"gold"}}."""
        return await get_client().put(f"/users/{user_id}.json", {"user": fields})

    @mcp.tool()
    async def update_many_users(user_ids: list[int], fields: Json) -> Json:
        """Apply the same update to up to 100 users. Returns a job_status."""
        return await get_client().put(
            "/users/update_many.json", {"user": fields}, params={"ids": _ids(user_ids)}
        )

    @mcp.tool()
    async def delete_user(user_id: int) -> Json:
        """Soft-delete a user (their tickets are kept)."""
        return await get_client().delete(f"/users/{user_id}.json")

    @mcp.tool()
    async def list_deleted_users(page_size: int = 100) -> Json:
        return await get_client().list("/deleted_users.json", "deleted_users", page_size=page_size)

    @mcp.tool()
    async def permanently_delete_user(user_id: int) -> Json:
        """IRREVERSIBLE (GDPR). Permanently delete an already-deleted user."""
        return await get_client().delete(f"/deleted_users/{user_id}.json")

    @mcp.tool()
    async def merge_users(source_user_id: int, target_user_id: int) -> Json:
        """Merge an end-user into another. The source user is removed."""
        return await get_client().put(
            f"/users/{source_user_id}/merge.json", {"user": {"id": target_user_id}}
        )

    @mcp.tool()
    async def get_user_related_info(user_id: int) -> Json:
        """Ticket counts (assigned, requested, ccd) for a user."""
        return await get_client().get(f"/users/{user_id}/related.json")

    @mcp.tool()
    async def set_user_password(user_id: int, password: str) -> Json:
        return await get_client().post(f"/users/{user_id}/password.json", {"password": password})

    @mcp.tool()
    async def change_user_password(user_id: int, previous_password: str, password: str) -> Json:
        return await get_client().put(
            f"/users/{user_id}/password.json",
            {"previous_password": previous_password, "password": password},
        )

    @mcp.tool()
    async def get_user_password_requirements(user_id: int) -> Json:
        return await get_client().get(f"/users/{user_id}/password/requirements.json")

    @mcp.tool()
    async def list_user_tags(user_id: int) -> Json:
        return await get_client().get(f"/users/{user_id}/tags.json")

    @mcp.tool()
    async def add_user_tags(user_id: int, tags: list[str]) -> Json:
        return await get_client().put(f"/users/{user_id}/tags.json", {"tags": tags})

    @mcp.tool()
    async def remove_user_tags(user_id: int, tags: list[str]) -> Json:
        return await get_client().delete(f"/users/{user_id}/tags.json", body={"tags": tags})

    # ------------------------------------------------------------ identities
    @mcp.tool()
    async def list_user_identities(user_id: int) -> Json:
        """Emails, phones, social identities of a user."""
        return await get_client().list(f"/users/{user_id}/identities.json", "identities")

    @mcp.tool()
    async def create_user_identity(
        user_id: int, type: str, value: str, verified: bool | None = None,
        primary: bool | None = None,
    ) -> Json:
        """Add an identity. type: email | twitter | facebook | google | phone_number | agent_forwarding."""
        ident = _clean({"type": type, "value": value, "verified": verified, "primary": primary})
        return await get_client().post(f"/users/{user_id}/identities.json", {"identity": ident})

    @mcp.tool()
    async def update_user_identity(user_id: int, identity_id: int, verified: bool | None = None,
                                   value: str | None = None) -> Json:
        return await get_client().put(
            f"/users/{user_id}/identities/{identity_id}.json",
            {"identity": _clean({"verified": verified, "value": value})},
        )

    @mcp.tool()
    async def make_identity_primary(user_id: int, identity_id: int) -> Json:
        return await get_client().put(f"/users/{user_id}/identities/{identity_id}/make_primary.json")

    @mcp.tool()
    async def verify_user_identity(user_id: int, identity_id: int) -> Json:
        return await get_client().put(f"/users/{user_id}/identities/{identity_id}/verify.json")

    @mcp.tool()
    async def request_identity_verification(user_id: int, identity_id: int) -> Json:
        """Send the verification email for an identity."""
        return await get_client().put(
            f"/users/{user_id}/identities/{identity_id}/request_verification.json"
        )

    @mcp.tool()
    async def delete_user_identity(user_id: int, identity_id: int) -> Json:
        return await get_client().delete(f"/users/{user_id}/identities/{identity_id}.json")

    # ----------------------------------------------------------------- misc
    @mcp.tool()
    async def list_user_sessions(user_id: int) -> Json:
        return await get_client().list(f"/users/{user_id}/sessions.json", "sessions")

    @mcp.tool()
    async def delete_user_sessions(user_id: int) -> Json:
        """Sign the user out of all sessions."""
        return await get_client().delete(f"/users/{user_id}/sessions.json")

    @mcp.tool()
    async def list_organization_memberships(
        user_id: int | None = None, organization_id: int | None = None
    ) -> Json:
        """Memberships linking users and organizations (filter by user or org)."""
        if user_id:
            path = f"/users/{user_id}/organization_memberships.json"
        elif organization_id:
            path = f"/organizations/{organization_id}/organization_memberships.json"
        else:
            path = "/organization_memberships.json"
        return await get_client().list(path, "organization_memberships")

    @mcp.tool()
    async def create_organization_membership(user_id: int, organization_id: int) -> Json:
        return await get_client().post(
            "/organization_memberships.json",
            {"organization_membership": {"user_id": user_id, "organization_id": organization_id}},
        )

    @mcp.tool()
    async def delete_organization_membership(membership_id: int) -> Json:
        return await get_client().delete(f"/organization_memberships/{membership_id}.json")

    @mcp.tool()
    async def make_organization_membership_default(user_id: int, membership_id: int) -> Json:
        return await get_client().put(
            f"/users/{user_id}/organization_memberships/{membership_id}/make_default.json"
        )

    @mcp.tool()
    async def list_user_activity(since: str | None = None) -> Json:
        """Agent activity stream for the authenticated user."""
        return await get_client().list("/activities.json", "activities", params={"since": since})
