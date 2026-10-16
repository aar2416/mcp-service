"""Ticket handling: tickets, comments, audits, tags, attachments, metrics, spam."""
from __future__ import annotations

import base64
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client


def _clean(d: Json) -> Json:
    return {k: v for k, v in d.items() if v is not None}


def _ids(ids: list[int]) -> str:
    return ",".join(str(i) for i in ids)


def register(mcp: FastMCP) -> None:
    # ------------------------------------------------------------------ read
    @mcp.tool()
    async def list_tickets(
        page_size: int = 100,
        max_pages: int = 1,
        page: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        external_id: str | None = None,
    ) -> Json:
        """List tickets (newest-first order configurable). sort_by: id, updated_at, created_at,
        status, subject, priority; sort_order: asc|desc. Use `search_tickets` for filtering."""
        return await get_client().list(
            "/tickets.json", "tickets", page_size=page_size, max_pages=max_pages, page=page,
            params={"sort_by": sort_by, "sort_order": sort_order, "external_id": external_id},
        )

    @mcp.tool()
    async def get_ticket(ticket_id: int, include: str | None = None) -> Json:
        """Get one ticket. `include` is an optional comma list of side-loads, e.g.
        'users,groups,organizations,comment_count,ticket_forms,brands'."""
        return await get_client().get(f"/tickets/{ticket_id}.json", {"include": include})

    @mcp.tool()
    async def get_many_tickets(ticket_ids: list[int]) -> Json:
        """Fetch up to 100 tickets by ID in a single call."""
        return await get_client().get("/tickets/show_many.json", {"ids": _ids(ticket_ids)})

    @mcp.tool()
    async def count_tickets() -> Json:
        """Approximate count of tickets in the account."""
        return await get_client().get("/tickets/count.json")

    @mcp.tool()
    async def list_tickets_for_user(
        user_id: int,
        relation: str = "requested",
        page_size: int = 100,
        max_pages: int = 1,
    ) -> Json:
        """List tickets tied to a user. relation: requested | ccd | followed | assigned."""
        if relation not in {"requested", "ccd", "followed", "assigned"}:
            raise ValueError("relation must be requested, ccd, followed or assigned")
        return await get_client().list(
            f"/users/{user_id}/tickets/{relation}.json", "tickets",
            page_size=page_size, max_pages=max_pages,
        )

    @mcp.tool()
    async def list_tickets_for_organization(
        organization_id: int, page_size: int = 100, max_pages: int = 1
    ) -> Json:
        """List tickets belonging to an organization."""
        return await get_client().list(
            f"/organizations/{organization_id}/tickets.json", "tickets",
            page_size=page_size, max_pages=max_pages,
        )

    @mcp.tool()
    async def list_recent_tickets(page_size: int = 100) -> Json:
        """Tickets the authenticated agent recently viewed."""
        return await get_client().list("/tickets/recent.json", "tickets", page_size=page_size)

    @mcp.tool()
    async def list_ticket_incidents(ticket_id: int) -> Json:
        """Incidents linked to a problem ticket."""
        return await get_client().list(f"/tickets/{ticket_id}/incidents.json", "tickets")

    @mcp.tool()
    async def list_problem_tickets() -> Json:
        """All tickets of type 'problem'."""
        return await get_client().list("/problems.json", "tickets")

    @mcp.tool()
    async def get_related_ticket_info(ticket_id: int) -> Json:
        """Related info for a ticket: followup sources, incident count, twitter/facebook refs."""
        return await get_client().get(f"/tickets/{ticket_id}/related.json")

    @mcp.tool()
    async def list_ticket_collaborators(ticket_id: int) -> Json:
        """Users who are collaborators (CCs) on the ticket."""
        return await get_client().get(f"/tickets/{ticket_id}/collaborators.json")

    @mcp.tool()
    async def list_ticket_followers(ticket_id: int) -> Json:
        return await get_client().get(f"/tickets/{ticket_id}/followers.json")

    @mcp.tool()
    async def list_ticket_email_ccs(ticket_id: int) -> Json:
        return await get_client().get(f"/tickets/{ticket_id}/email_ccs.json")

    # ----------------------------------------------------------------- write
    @mcp.tool()
    async def create_ticket(
        subject: str,
        comment_body: str,
        requester_email: str | None = None,
        requester_name: str | None = None,
        requester_id: int | None = None,
        public: bool = True,
        html_body: str | None = None,
        priority: str | None = None,
        type: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        assignee_id: int | None = None,
        assignee_email: str | None = None,
        group_id: int | None = None,
        organization_id: int | None = None,
        brand_id: int | None = None,
        ticket_form_id: int | None = None,
        custom_fields: list[Json] | None = None,
        due_at: str | None = None,
        external_id: str | None = None,
        collaborators: list[Any] | None = None,
        follower_ids: list[int] | None = None,
        uploads: list[str] | None = None,
        extra: Json | None = None,
    ) -> Json:
        """Create a ticket. priority: urgent|high|normal|low. type: problem|incident|question|task.
        status: new|open|pending|hold|solved. custom_fields: [{"id": 123, "value": "x"}].
        uploads: attachment tokens from `upload_attachment`. `extra` merges arbitrary
        ticket attributes (e.g. via, problem_id, macro_ids)."""
        comment = _clean({
            "body": comment_body, "html_body": html_body, "public": public, "uploads": uploads,
        })
        requester = None
        if requester_email and not requester_id:
            requester = _clean({"email": requester_email, "name": requester_name})
        ticket = _clean({
            "subject": subject, "comment": comment, "requester": requester,
            "requester_id": requester_id, "priority": priority, "type": type, "status": status,
            "tags": tags, "assignee_id": assignee_id, "assignee_email": assignee_email,
            "group_id": group_id, "organization_id": organization_id, "brand_id": brand_id,
            "ticket_form_id": ticket_form_id, "custom_fields": custom_fields, "due_at": due_at,
            "external_id": external_id, "collaborators": collaborators,
            "follower_ids": follower_ids,
        })
        ticket.update(extra or {})
        return await get_client().post("/tickets.json", {"ticket": ticket})

    @mcp.tool()
    async def update_ticket(
        ticket_id: int,
        subject: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        type: str | None = None,
        assignee_id: int | None = None,
        group_id: int | None = None,
        requester_id: int | None = None,
        organization_id: int | None = None,
        tags: list[str] | None = None,
        additional_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        custom_fields: list[Json] | None = None,
        comment_body: str | None = None,
        comment_public: bool = True,
        comment_html_body: str | None = None,
        comment_author_id: int | None = None,
        uploads: list[str] | None = None,
        due_at: str | None = None,
        problem_id: int | None = None,
        macro_ids: list[int] | None = None,
        extra: Json | None = None,
    ) -> Json:
        """Update a ticket and/or add a reply. `tags` replaces all tags; use additional_tags /
        remove_tags to modify. To reply: set comment_body (comment_public=False for an internal
        note). To solve: status='solved'. `extra` merges arbitrary ticket attributes."""
        comment = None
        if comment_body or comment_html_body:
            comment = _clean({
                "body": comment_body, "html_body": comment_html_body, "public": comment_public,
                "author_id": comment_author_id, "uploads": uploads,
            })
        ticket = _clean({
            "subject": subject, "status": status, "priority": priority, "type": type,
            "assignee_id": assignee_id, "group_id": group_id, "requester_id": requester_id,
            "organization_id": organization_id, "tags": tags,
            "additional_tags": additional_tags, "remove_tags": remove_tags,
            "custom_fields": custom_fields, "comment": comment, "due_at": due_at,
            "problem_id": problem_id, "macro_ids": macro_ids,
        })
        ticket.update(extra or {})
        return await get_client().put(f"/tickets/{ticket_id}.json", {"ticket": ticket})

    @mcp.tool()
    async def add_ticket_comment(
        ticket_id: int,
        body: str,
        public: bool = True,
        html_body: str | None = None,
        author_id: int | None = None,
        uploads: list[str] | None = None,
    ) -> Json:
        """Add a public reply or (public=false) internal note to a ticket."""
        comment = _clean({
            "body": body, "html_body": html_body, "public": public,
            "author_id": author_id, "uploads": uploads,
        })
        return await get_client().put(f"/tickets/{ticket_id}.json", {"ticket": {"comment": comment}})

    @mcp.tool()
    async def delete_ticket(ticket_id: int) -> Json:
        """Soft-delete a ticket (recoverable for 30 days via `restore_ticket`)."""
        return await get_client().delete(f"/tickets/{ticket_id}.json")

    @mcp.tool()
    async def restore_ticket(ticket_id: int) -> Json:
        """Restore a soft-deleted ticket."""
        return await get_client().put(f"/deleted_tickets/{ticket_id}/restore.json")

    @mcp.tool()
    async def restore_many_tickets(ticket_ids: list[int]) -> Json:
        return await get_client().put("/deleted_tickets/restore_many.json", params={"ids": _ids(ticket_ids)})

    @mcp.tool()
    async def list_deleted_tickets(
        sort_by: str | None = None, sort_order: str | None = None, page_size: int = 100
    ) -> Json:
        """List soft-deleted tickets."""
        return await get_client().list(
            "/deleted_tickets.json", "deleted_tickets", page_size=page_size,
            params={"sort_by": sort_by, "sort_order": sort_order},
        )

    @mcp.tool()
    async def permanently_delete_ticket(ticket_id: int) -> Json:
        """IRREVERSIBLE. Permanently delete an already soft-deleted ticket."""
        return await get_client().delete(f"/deleted_tickets/{ticket_id}.json")

    @mcp.tool()
    async def permanently_delete_many_tickets(ticket_ids: list[int]) -> Json:
        """IRREVERSIBLE. Permanently delete up to 100 soft-deleted tickets."""
        return await get_client().delete("/deleted_tickets/destroy_many.json", params={"ids": _ids(ticket_ids)})

    # ------------------------------------------------------------------ bulk
    @mcp.tool()
    async def create_many_tickets(tickets: list[Json]) -> Json:
        """Create up to 100 tickets. Each item is a full ticket object. Returns a job_status."""
        return await get_client().post("/tickets/create_many.json", {"tickets": tickets})

    @mcp.tool()
    async def update_many_tickets(ticket_ids: list[int], fields: Json) -> Json:
        """Apply the same update (e.g. {"status":"solved","additional_tags":["x"]}) to up to 100
        tickets. Returns a job_status."""
        return await get_client().put(
            "/tickets/update_many.json", {"ticket": fields}, params={"ids": _ids(ticket_ids)}
        )

    @mcp.tool()
    async def update_many_tickets_individually(updates: list[Json]) -> Json:
        """Batch update where each item is {"id": 1, ...fields}. Up to 100. Returns a job_status."""
        return await get_client().put("/tickets/update_many.json", {"tickets": updates})

    @mcp.tool()
    async def bulk_delete_tickets(ticket_ids: list[int]) -> Json:
        """Soft-delete up to 100 tickets. Returns a job_status."""
        return await get_client().delete("/tickets/destroy_many.json", params={"ids": _ids(ticket_ids)})

    @mcp.tool()
    async def merge_tickets(
        target_ticket_id: int,
        source_ticket_ids: list[int],
        target_comment: str | None = None,
        source_comment: str | None = None,
        target_comment_is_public: bool = False,
        source_comment_is_public: bool = False,
    ) -> Json:
        """Merge source tickets INTO the target ticket (sources get closed). Returns a job_status."""
        body = _clean({
            "ids": source_ticket_ids, "target_comment": target_comment,
            "source_comment": source_comment,
            "target_comment_is_public": target_comment_is_public,
            "source_comment_is_public": source_comment_is_public,
        })
        return await get_client().post(f"/tickets/{target_ticket_id}/merge.json", body)

    @mcp.tool()
    async def mark_ticket_as_spam(ticket_id: int) -> Json:
        """Mark a ticket as spam and suspend the requester."""
        return await get_client().put(f"/tickets/{ticket_id}/mark_as_spam.json")

    @mcp.tool()
    async def mark_many_tickets_as_spam(ticket_ids: list[int]) -> Json:
        return await get_client().put("/tickets/mark_many_as_spam.json", params={"ids": _ids(ticket_ids)})

    # -------------------------------------------------------------- comments
    @mcp.tool()
    async def list_ticket_comments(
        ticket_id: int,
        sort_order: str = "asc",
        include_inline_images: bool = False,
        include: str | None = None,
        page_size: int = 100,
        max_pages: int = 1,
    ) -> Json:
        """All comments (public replies + internal notes) on a ticket, with attachments.
        include='users' side-loads authors."""
        return await get_client().list(
            f"/tickets/{ticket_id}/comments.json", "comments", page_size=page_size,
            max_pages=max_pages,
            params={"sort_order": sort_order, "include_inline_images": include_inline_images or None,
                    "include": include},
        )

    @mcp.tool()
    async def make_comment_private(ticket_id: int, comment_id: int) -> Json:
        """Convert a public comment to an internal note (irreversible)."""
        return await get_client().put(f"/tickets/{ticket_id}/comments/{comment_id}/make_private.json")

    @mcp.tool()
    async def redact_comment(ticket_id: int, comment_id: int, text: str) -> Json:
        """Permanently redact `text` from a comment body (e.g. credit card numbers)."""
        return await get_client().put(
            f"/tickets/{ticket_id}/comments/{comment_id}/redact.json", {"text": text}
        )

    @mcp.tool()
    async def redact_comment_attachment(ticket_id: int, comment_id: int, attachment_id: int) -> Json:
        """Permanently delete one attachment from a comment."""
        return await get_client().put(
            f"/tickets/{ticket_id}/comments/{comment_id}/attachments/{attachment_id}/redact.json"
        )

    # ---------------------------------------------------------------- audits
    @mcp.tool()
    async def list_ticket_audits(ticket_id: int, page_size: int = 100, max_pages: int = 1) -> Json:
        """Immutable history of every change/event on a ticket."""
        return await get_client().list(
            f"/tickets/{ticket_id}/audits.json", "audits", page_size=page_size, max_pages=max_pages
        )

    @mcp.tool()
    async def get_ticket_audit(ticket_id: int, audit_id: int) -> Json:
        return await get_client().get(f"/tickets/{ticket_id}/audits/{audit_id}.json")

    @mcp.tool()
    async def list_all_ticket_audits(limit: int = 100, cursor: str | None = None) -> Json:
        """Account-wide audit stream (cursor paginated, newest first)."""
        return await get_client().get(
            "/ticket_audits.json", {"limit": limit, "cursor": cursor}
        )

    # ------------------------------------------------------------------ tags
    @mcp.tool()
    async def get_ticket_tags(ticket_id: int) -> Json:
        return await get_client().get(f"/tickets/{ticket_id}/tags.json")

    @mcp.tool()
    async def add_ticket_tags(ticket_id: int, tags: list[str]) -> Json:
        """Add tags, keeping existing ones."""
        return await get_client().put(f"/tickets/{ticket_id}/tags.json", {"tags": tags})

    @mcp.tool()
    async def set_ticket_tags(ticket_id: int, tags: list[str]) -> Json:
        """REPLACE all tags on the ticket."""
        return await get_client().post(f"/tickets/{ticket_id}/tags.json", {"tags": tags})

    @mcp.tool()
    async def remove_ticket_tags(ticket_id: int, tags: list[str]) -> Json:
        return await get_client().delete(f"/tickets/{ticket_id}/tags.json", body={"tags": tags})

    # --------------------------------------------------------------- metrics
    @mcp.tool()
    async def list_ticket_metrics(page_size: int = 100, max_pages: int = 1) -> Json:
        """Reply/resolution times, reopens, replies for all tickets."""
        return await get_client().list(
            "/ticket_metrics.json", "ticket_metrics", page_size=page_size, max_pages=max_pages
        )

    @mcp.tool()
    async def get_ticket_metrics(ticket_id: int) -> Json:
        """Reply time, full resolution time, wait times, reopens for a single ticket."""
        return await get_client().get(f"/tickets/{ticket_id}/metrics.json")

    # ----------------------------------------------------------- attachments
    @mcp.tool()
    async def upload_attachment(
        filename: str,
        content_base64: str | None = None,
        file_path: str | None = None,
        content_type: str = "application/binary",
        token: str | None = None,
    ) -> Json:
        """Upload a file and get an upload `token` to pass as `uploads=[token]` to
        create_ticket / update_ticket / add_ticket_comment. Provide content_base64 or a
        file_path readable by the server. Pass an existing `token` to add more files to it."""
        if content_base64:
            data = base64.b64decode(content_base64)
        elif file_path:
            with open(os.path.expanduser(file_path), "rb") as fh:
                data = fh.read()
        else:
            raise ValueError("Provide content_base64 or file_path")
        return await get_client().request(
            "POST", "/uploads.json", params={"filename": filename, "token": token},
            content=data, headers={"Content-Type": content_type},
        )

    @mcp.tool()
    async def delete_upload(token: str) -> Json:
        """Delete an unused upload token and its files."""
        return await get_client().delete(f"/uploads/{token}.json")

    @mcp.tool()
    async def get_attachment(attachment_id: int) -> Json:
        """Attachment metadata including content_url."""
        return await get_client().get(f"/attachments/{attachment_id}.json")

    # ------------------------------------------------------------ suspended
    @mcp.tool()
    async def list_suspended_tickets(
        sort_by: str | None = None, sort_order: str | None = None,
        page_size: int = 100, max_pages: int = 1,
    ) -> Json:
        """Tickets held in the suspended queue (spam / unverified senders)."""
        return await get_client().list(
            "/suspended_tickets.json", "suspended_tickets", page_size=page_size,
            max_pages=max_pages, params={"sort_by": sort_by, "sort_order": sort_order},
        )

    @mcp.tool()
    async def get_suspended_ticket(suspended_ticket_id: int) -> Json:
        return await get_client().get(f"/suspended_tickets/{suspended_ticket_id}.json")

    @mcp.tool()
    async def recover_suspended_ticket(suspended_ticket_id: int) -> Json:
        """Turn a suspended ticket into a real ticket."""
        return await get_client().put(f"/suspended_tickets/{suspended_ticket_id}/recover.json")

    @mcp.tool()
    async def recover_many_suspended_tickets(suspended_ticket_ids: list[int]) -> Json:
        return await get_client().put(
            "/suspended_tickets/recover_many.json", params={"ids": _ids(suspended_ticket_ids)}
        )

    @mcp.tool()
    async def delete_suspended_ticket(suspended_ticket_id: int) -> Json:
        return await get_client().delete(f"/suspended_tickets/{suspended_ticket_id}.json")

    @mcp.tool()
    async def delete_many_suspended_tickets(suspended_ticket_ids: list[int]) -> Json:
        return await get_client().delete(
            "/suspended_tickets/destroy_many.json", params={"ids": _ids(suspended_ticket_ids)}
        )

    # ---------------------------------------------------- requests (end user)
    @mcp.tool()
    async def list_requests(
        status: str | None = None, organization_id: int | None = None,
        user_id: int | None = None, page_size: int = 100, max_pages: int = 1,
    ) -> Json:
        """Tickets as seen by end users ('requests'). status e.g. 'open,pending' or 'solved'."""
        if user_id:
            path = f"/users/{user_id}/requests.json"
        elif organization_id:
            path = f"/organizations/{organization_id}/requests.json"
        else:
            path = "/requests.json"
        return await get_client().list(
            path, "requests", page_size=page_size, max_pages=max_pages, params={"status": status}
        )

    @mcp.tool()
    async def get_request(request_id: int) -> Json:
        return await get_client().get(f"/requests/{request_id}.json")

    @mcp.tool()
    async def list_request_comments(request_id: int) -> Json:
        return await get_client().list(f"/requests/{request_id}/comments.json", "comments")

    # ---------------------------------------------------------- ticket skips
    @mcp.tool()
    async def list_ticket_skips(ticket_id: int | None = None, user_id: int | None = None) -> Json:
        """Record of agents skipping tickets in Play mode."""
        if ticket_id:
            path = f"/tickets/{ticket_id}/skips.json"
        elif user_id:
            path = f"/users/{user_id}/skips.json"
        else:
            path = "/skips.json"
        return await get_client().list(path, "skips")
