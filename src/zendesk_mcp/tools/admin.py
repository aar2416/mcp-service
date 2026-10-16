"""Configuration & automation objects: fields, forms, views, macros, triggers, automations,
brands, SLAs, webhooks, schedules, custom roles/objects, satisfaction, account-level data."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def _ids(ids: list[int]) -> str:
    return ",".join(str(i) for i in ids)


def crud(
    mcp: FastMCP,
    plural: str,
    singular: str,
    *,
    base: str | None = None,
    list_key: str | None = None,
    wrap: str | None = None,
    suffix: str = ".json",
    update_method: str = "PUT",
    ops: str = "lgcud",
    what: str | None = None,
    create_hint: str = "",
) -> None:
    """Register list/get/create/update/delete tools for a standard Zendesk resource.

    ops is any subset of l(ist) g(et) c(reate) u(pdate) d(elete).
    """
    base = base or f"/{plural}"
    list_key = list_key or plural
    wrap = wrap or singular
    what = what or singular.replace("_", " ")
    item = lambda i: f"{base}/{i}{suffix}"  # noqa: E731

    if "l" in ops:
        @mcp.tool(name=f"list_{plural}", description=f"List {what}s. Returns {{'{list_key}': [...]}}.")
        async def _list(page_size: int = 100, max_pages: int = 1, page: int | None = None) -> Json:
            return await get_client().list(
                f"{base}{suffix}", list_key, page_size=page_size, max_pages=max_pages, page=page
            )

    if "g" in ops:
        @mcp.tool(name=f"get_{singular}", description=f"Get one {what} by ID.")
        async def _get(id: int) -> Json:
            return await get_client().get(item(id))

    if "c" in ops:
        @mcp.tool(
            name=f"create_{singular}",
            description=f"Create a {what}. `data` is the {wrap} object as documented by Zendesk. {create_hint}",
        )
        async def _create(data: Json) -> Json:
            return await get_client().post(f"{base}{suffix}", {wrap: data})

    if "u" in ops:
        @mcp.tool(name=f"update_{singular}", description=f"Update a {what}. `data` holds only the fields to change.")
        async def _update(id: int, data: Json) -> Json:
            return await get_client().request(update_method, item(id), json={wrap: data})

    if "d" in ops:
        @mcp.tool(name=f"delete_{singular}", description=f"Delete a {what} by ID.")
        async def _delete(id: int) -> Json:
            return await get_client().delete(item(id))


def register(mcp: FastMCP) -> None:
    # ---------------------------------------------------------------- fields
    crud(mcp, "ticket_fields", "ticket_field", what="ticket field",
         create_hint='e.g. {"type":"tagger","title":"Plan","custom_field_options":[{"name":"Gold","value":"gold"}]}')
    crud(mcp, "ticket_forms", "ticket_form", what="ticket form")
    crud(mcp, "user_fields", "user_field", what="custom user field", wrap="user_field")
    crud(mcp, "organization_fields", "organization_field", what="custom organization field")

    @mcp.tool()
    async def list_ticket_field_options(ticket_field_id: int) -> Json:
        """Dropdown options for a custom tagger/multiselect ticket field."""
        return await get_client().list(f"/ticket_fields/{ticket_field_id}/options.json", "custom_field_options")

    @mcp.tool()
    async def upsert_ticket_field_option(ticket_field_id: int, name: str, value: str, id: int | None = None) -> Json:
        """Create (or update when `id` given) a dropdown option on a ticket field."""
        opt: Json = {"name": name, "value": value}
        if id:
            opt["id"] = id
        return await get_client().post(
            f"/ticket_fields/{ticket_field_id}/options.json", {"custom_field_option": opt}
        )

    @mcp.tool()
    async def delete_ticket_field_option(ticket_field_id: int, option_id: int) -> Json:
        return await get_client().delete(f"/ticket_fields/{ticket_field_id}/options/{option_id}.json")

    @mcp.tool()
    async def clone_ticket_form(ticket_form_id: int) -> Json:
        return await get_client().post(f"/ticket_forms/{ticket_form_id}/clone.json")

    @mcp.tool()
    async def list_user_field_options(user_field_id: int) -> Json:
        return await get_client().list(f"/user_fields/{user_field_id}/options.json", "custom_field_options")

    # ----------------------------------------------------------------- views
    crud(mcp, "views", "view", what="view")

    @mcp.tool()
    async def list_active_views() -> Json:
        return await get_client().list("/views/active.json", "views")

    @mcp.tool()
    async def search_views(query: str) -> Json:
        return await get_client().list("/views/search.json", "views", params={"query": query})

    @mcp.tool()
    async def get_view_tickets(view_id: int, page_size: int = 100, max_pages: int = 1) -> Json:
        """Run a view and return its tickets (e.g. 'Unassigned tickets')."""
        return await get_client().list(
            f"/views/{view_id}/tickets.json", "tickets", page_size=page_size, max_pages=max_pages
        )

    @mcp.tool()
    async def execute_view(view_id: int, page_size: int = 100) -> Json:
        """Run a view and return rows plus column metadata."""
        return await get_client().list(f"/views/{view_id}/execute.json", "rows", page_size=page_size)

    @mcp.tool()
    async def count_view_tickets(view_id: int) -> Json:
        return await get_client().get(f"/views/{view_id}/count.json")

    @mcp.tool()
    async def count_many_views(view_ids: list[int]) -> Json:
        return await get_client().get("/views/count_many.json", {"ids": _ids(view_ids)})

    # ---------------------------------------------------------------- macros
    crud(mcp, "macros", "macro", what="macro")

    @mcp.tool()
    async def search_macros(query: str, active: bool | None = None) -> Json:
        return await get_client().list(
            "/macros/search.json", "macros", params={"query": query, "active": active}
        )

    @mcp.tool()
    async def list_macro_categories() -> Json:
        return await get_client().get("/macros/categories.json")

    @mcp.tool()
    async def preview_macro_on_ticket(macro_id: int, ticket_id: int) -> Json:
        """Show the changes a macro WOULD make to a ticket (does not apply them)."""
        return await get_client().get(f"/tickets/{ticket_id}/macros/{macro_id}/apply.json")

    @mcp.tool()
    async def apply_macro_to_ticket(macro_id: int, ticket_id: int) -> Json:
        """Apply a macro to a ticket: previews the result, then saves it with update_ticket."""
        c = get_client()
        preview = await c.get(f"/tickets/{ticket_id}/macros/{macro_id}/apply.json")
        result = preview.get("result", {})
        ticket = result.get("ticket", {})
        if not ticket:
            return preview
        return await c.put(f"/tickets/{ticket_id}.json", {"ticket": ticket})

    # ----------------------------------------------------- triggers/automations
    crud(mcp, "triggers", "trigger", what="trigger")
    crud(mcp, "automations", "automation", what="automation")

    @mcp.tool()
    async def search_triggers(query: str, active: bool | None = None) -> Json:
        return await get_client().list(
            "/triggers/search.json", "triggers", params={"query": query, "active": active}
        )

    @mcp.tool()
    async def list_trigger_categories() -> Json:
        return await get_client().list("/trigger_categories.json", "trigger_categories")

    @mcp.tool()
    async def list_active_triggers() -> Json:
        return await get_client().list("/triggers/active.json", "triggers")

    @mcp.tool()
    async def list_active_automations() -> Json:
        return await get_client().list("/automations/active.json", "automations")

    @mcp.tool()
    async def search_automations(query: str) -> Json:
        return await get_client().list("/automations/search.json", "automations", params={"query": query})

    # ------------------------------------------------------ account structure
    crud(mcp, "brands", "brand", what="brand")
    crud(mcp, "custom_roles", "custom_role", what="custom agent role")
    crud(mcp, "sla_policies", "sla_policy", base="/slas/policies", what="SLA policy")
    crud(mcp, "schedules", "schedule", base="/business_hours/schedules", what="business-hours schedule")
    crud(mcp, "support_addresses", "support_address", base="/recipient_addresses",
         list_key="recipient_addresses", wrap="recipient_address", what="support (recipient) address")
    crud(mcp, "dynamic_content_items", "dynamic_content_item", base="/dynamic_content/items",
         list_key="items", wrap="item", what="dynamic content item")
    crud(mcp, "targets", "target", what="target (legacy notification integration)")
    crud(mcp, "bookmarks", "bookmark", ops="lcd", what="ticket bookmark")
    crud(mcp, "webhooks", "webhook", suffix="", update_method="PATCH", what="webhook",
         create_hint='e.g. {"name":"n","endpoint":"https://..","http_method":"POST","request_format":"json","status":"active","subscriptions":["zen:event-type:ticket.created"]}')

    @mcp.tool()
    async def check_host_mapping(brand_id: int, subdomain: str) -> Json:
        return await get_client().get(f"/brands/{brand_id}/check_host_mapping.json", {"subdomain": subdomain})

    @mcp.tool()
    async def list_schedule_holidays(schedule_id: int) -> Json:
        return await get_client().list(f"/business_hours/schedules/{schedule_id}/holidays.json", "holidays")

    @mcp.tool()
    async def set_schedule_hours(schedule_id: int, intervals: list[Json]) -> Json:
        """Replace weekly work hours. intervals: [{"start_time":1980,"end_time":2460}] in minutes since Sunday 00:00."""
        return await get_client().put(
            f"/business_hours/schedules/{schedule_id}/workweek.json", {"workweek": {"intervals": intervals}}
        )

    @mcp.tool()
    async def create_schedule_holiday(schedule_id: int, name: str, start_date: str, end_date: str) -> Json:
        return await get_client().post(
            f"/business_hours/schedules/{schedule_id}/holidays.json",
            {"holiday": {"name": name, "start_date": start_date, "end_date": end_date}},
        )

    @mcp.tool()
    async def delete_schedule_holiday(schedule_id: int, holiday_id: int) -> Json:
        return await get_client().delete(f"/business_hours/schedules/{schedule_id}/holidays/{holiday_id}.json")

    @mcp.tool()
    async def test_webhook(webhook_id: str | None = None, request: Json | None = None) -> Json:
        """Send a test request. `request` = {"endpoint":..,"http_method":..,"request_format":..,"authentication":..}."""
        return await get_client().post(
            "/webhooks/test", {"request": request or {}}, params={"webhook_id": webhook_id}
        )

    @mcp.tool()
    async def get_webhook_signing_secret(webhook_id: str) -> Json:
        return await get_client().get(f"/webhooks/{webhook_id}/signing_secret")

    @mcp.tool()
    async def reset_webhook_signing_secret(webhook_id: str) -> Json:
        return await get_client().post(f"/webhooks/{webhook_id}/signing_secret")

    @mcp.tool()
    async def list_webhook_invocations(webhook_id: str, status: str | None = None) -> Json:
        """Recent deliveries for a webhook (debug failures). status: success|failure."""
        return await get_client().get(
            f"/webhooks/{webhook_id}/invocations", {"filter[status]": status}
        )

    @mcp.tool()
    async def list_sla_policy_definitions() -> Json:
        """Valid filter/metric definitions for building SLA policies."""
        return await get_client().get("/slas/policies/definitions.json")

    # -------------------------------------------------------- custom objects
    @mcp.tool()
    async def list_custom_objects() -> Json:
        return await get_client().get("/custom_objects")

    @mcp.tool()
    async def list_custom_object_records(
        custom_object_key: str, page_size: int = 100, after_cursor: str | None = None,
        filter: Json | None = None,
    ) -> Json:
        """Records of a custom object. `filter` optional e.g. {"name":"x"}."""
        params: Json = {"page[size]": page_size, "page[after]": after_cursor}
        if filter:
            import json as _json
            params["filter"] = _json.dumps(filter)
        return await get_client().get(f"/custom_objects/{custom_object_key}/records", params)

    @mcp.tool()
    async def get_custom_object_record(custom_object_key: str, record_id: str) -> Json:
        return await get_client().get(f"/custom_objects/{custom_object_key}/records/{record_id}")

    @mcp.tool()
    async def create_custom_object_record(custom_object_key: str, record: Json) -> Json:
        """record e.g. {"name":"x","custom_object_fields":{"field_key":"v"}}."""
        return await get_client().post(
            f"/custom_objects/{custom_object_key}/records", {"custom_object_record": record}
        )

    @mcp.tool()
    async def update_custom_object_record(custom_object_key: str, record_id: str, record: Json) -> Json:
        return await get_client().request(
            "PATCH", f"/custom_objects/{custom_object_key}/records/{record_id}",
            json={"custom_object_record": record},
            headers={"Content-Type": "application/merge-patch+json"},
        )

    @mcp.tool()
    async def delete_custom_object_record(custom_object_key: str, record_id: str) -> Json:
        return await get_client().delete(f"/custom_objects/{custom_object_key}/records/{record_id}")

    @mcp.tool()
    async def search_custom_object_records(custom_object_key: str, query: str) -> Json:
        return await get_client().get(
            f"/custom_objects/{custom_object_key}/records/search", {"query": query}
        )

    # -------------------------------------------------------- satisfaction/CSAT
    @mcp.tool()
    async def list_satisfaction_ratings(
        score: str | None = None, start_time: int | None = None, end_time: int | None = None,
        page_size: int = 100, max_pages: int = 1,
    ) -> Json:
        """CSAT ratings. score: good|bad|offered|received|good_with_comment|bad_with_comment."""
        return await get_client().list(
            "/satisfaction_ratings.json", "satisfaction_ratings", page_size=page_size,
            max_pages=max_pages,
            params={"score": score, "start_time": start_time, "end_time": end_time},
        )

    @mcp.tool()
    async def get_satisfaction_rating(rating_id: int) -> Json:
        return await get_client().get(f"/satisfaction_ratings/{rating_id}.json")

    @mcp.tool()
    async def create_satisfaction_rating(
        ticket_id: int, score: str, comment: str | None = None, reason_code: int | None = None
    ) -> Json:
        """Record a rating for a solved ticket. score: good | bad."""
        rating: Json = {"score": score}
        if comment:
            rating["comment"] = comment
        if reason_code:
            rating["reason_code"] = reason_code
        return await get_client().post(
            f"/tickets/{ticket_id}/satisfaction_rating.json", {"satisfaction_rating": rating}
        )

    @mcp.tool()
    async def list_satisfaction_reasons() -> Json:
        return await get_client().list("/satisfaction_reasons.json", "reasons")

    # ------------------------------------------------------------ account-wide
    @mcp.tool()
    async def get_account_settings() -> Json:
        return await get_client().get("/account/settings.json")

    @mcp.tool()
    async def update_account_settings(settings: Json) -> Json:
        """e.g. {"tickets": {"collaboration": true}}."""
        return await get_client().put("/account/settings.json", {"settings": settings})

    @mcp.tool()
    async def list_locales() -> Json:
        return await get_client().get("/locales.json")

    @mcp.tool()
    async def list_account_tags(page_size: int = 100) -> Json:
        """Most-used tags across the account with counts."""
        return await get_client().list("/tags.json", "tags", page_size=page_size)

    @mcp.tool()
    async def list_audit_logs(
        filter_action: str | None = None, filter_actor_id: int | None = None,
        filter_source_type: str | None = None, filter_created_at: list[str] | None = None,
        page_size: int = 100, max_pages: int = 1,
    ) -> Json:
        """Admin audit log (who changed what). filter_created_at: [start_iso, end_iso]."""
        params: Json = {
            "filter[action]": filter_action, "filter[actor_id]": filter_actor_id,
            "filter[source_type]": filter_source_type,
        }
        if filter_created_at:
            params["filter[created_at][]"] = filter_created_at
        return await get_client().list(
            "/audit_logs.json", "audit_logs", params=params, page_size=page_size, max_pages=max_pages
        )

    @mcp.tool()
    async def get_audit_log(audit_log_id: int) -> Json:
        return await get_client().get(f"/audit_logs/{audit_log_id}.json")

    @mcp.tool()
    async def list_job_statuses() -> Json:
        return await get_client().list("/job_statuses.json", "job_statuses")

    @mcp.tool()
    async def get_job_status(job_id: str) -> Json:
        """Poll a bulk operation (update_many, merge, create_many...) started earlier."""
        return await get_client().get(f"/job_statuses/{job_id}.json")

    @mcp.tool()
    async def list_sessions() -> Json:
        return await get_client().list("/sessions.json", "sessions")

    @mcp.tool()
    async def list_sharing_agreements() -> Json:
        return await get_client().get("/sharing_agreements.json")
