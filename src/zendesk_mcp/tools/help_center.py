"""Help Center (Guide): categories, sections, articles, comments, votes, community posts."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import Json, get_client
from .admin import crud

HC = "/help_center"


def _clean(d: Json) -> Json:
    return {k: v for k, v in d.items() if v is not None}


def register(mcp: FastMCP) -> None:
    # -------------------------------------------------------------- articles
    @mcp.tool()
    async def list_articles(
        locale: str | None = None, section_id: int | None = None, category_id: int | None = None,
        label_names: str | None = None, sort_by: str | None = None, sort_order: str | None = None,
        page_size: int = 100, max_pages: int = 1,
    ) -> Json:
        """List Help Center articles, optionally within a section or category."""
        base = HC + (f"/{locale}" if locale else "")
        if section_id:
            path = f"{base}/sections/{section_id}/articles.json"
        elif category_id:
            path = f"{base}/categories/{category_id}/articles.json"
        else:
            path = f"{base}/articles.json"
        return await get_client().list(
            path, "articles", page_size=page_size, max_pages=max_pages,
            params={"label_names": label_names, "sort_by": sort_by, "sort_order": sort_order},
        )

    @mcp.tool()
    async def get_article(article_id: int, locale: str | None = None) -> Json:
        base = HC + (f"/{locale}" if locale else "")
        return await get_client().get(f"{base}/articles/{article_id}.json")

    @mcp.tool()
    async def search_articles(
        query: str, locale: str | None = None, category: int | None = None,
        section: int | None = None, label_names: str | None = None, page_size: int = 25,
    ) -> Json:
        """Full-text search of published Help Center articles."""
        return await get_client().get(
            f"{HC}/articles/search.json",
            {"query": query, "locale": locale, "category": category, "section": section,
             "label_names": label_names, "per_page": page_size},
        )

    @mcp.tool()
    async def create_article(
        section_id: int,
        title: str,
        body: str,
        locale: str = "en-us",
        draft: bool = True,
        permission_group_id: int | None = None,
        user_segment_id: int | None = None,
        label_names: list[str] | None = None,
        promoted: bool | None = None,
        comments_disabled: bool | None = None,
        notify_subscribers: bool = False,
    ) -> Json:
        """Create an article in a section (HTML body). Defaults to a draft."""
        article = _clean({
            "title": title, "body": body, "locale": locale, "draft": draft,
            "user_segment_id": user_segment_id, "label_names": label_names,
            "promoted": promoted, "comments_disabled": comments_disabled,
        })
        payload: Json = {"article": article, "notify_subscribers": notify_subscribers}
        if permission_group_id:
            payload["article"]["permission_group_id"] = permission_group_id
        return await get_client().post(f"{HC}/sections/{section_id}/articles.json", payload)

    @mcp.tool()
    async def update_article(article_id: int, fields: Json) -> Json:
        """Update article metadata (section_id, draft, promoted, label_names, user_segment_id,
        author_id, comments_disabled...). To change title/body use `update_article_translation`."""
        return await get_client().put(f"{HC}/articles/{article_id}.json", {"article": fields})

    @mcp.tool()
    async def update_article_translation(article_id: int, locale: str, fields: Json) -> Json:
        """Edit title/body (HTML) of an article in one locale, e.g. {"title":"x","body":"<p>..</p>"}."""
        return await get_client().put(
            f"{HC}/articles/{article_id}/translations/{locale}.json", {"translation": fields}
        )

    @mcp.tool()
    async def create_article_translation(article_id: int, locale: str, title: str, body: str, draft: bool = True) -> Json:
        return await get_client().post(
            f"{HC}/articles/{article_id}/translations.json",
            {"translation": {"locale": locale, "title": title, "body": body, "draft": draft}},
        )

    @mcp.tool()
    async def list_article_translations(article_id: int) -> Json:
        return await get_client().list(f"{HC}/articles/{article_id}/translations.json", "translations")

    @mcp.tool()
    async def archive_article(article_id: int) -> Json:
        """Archive (delete) an article. Archived articles can be restored in the UI."""
        return await get_client().delete(f"{HC}/articles/{article_id}.json")

    @mcp.tool()
    async def list_article_labels() -> Json:
        return await get_client().list(f"{HC}/articles/labels.json", "labels")

    @mcp.tool()
    async def list_article_attachments(article_id: int) -> Json:
        return await get_client().list(f"{HC}/articles/{article_id}/attachments.json", "article_attachments")

    @mcp.tool()
    async def delete_article_attachment(attachment_id: int) -> Json:
        return await get_client().delete(f"{HC}/articles/attachments/{attachment_id}.json")

    # ------------------------------------------------- article comments / votes
    @mcp.tool()
    async def list_article_comments(article_id: int, locale: str | None = None) -> Json:
        base = HC + (f"/{locale}" if locale else "")
        return await get_client().list(f"{base}/articles/{article_id}/comments.json", "comments")

    @mcp.tool()
    async def create_article_comment(article_id: int, body: str, locale: str = "en-us") -> Json:
        return await get_client().post(
            f"{HC}/articles/{article_id}/comments.json",
            {"comment": {"body": body, "locale": locale}},
        )

    @mcp.tool()
    async def vote_article(article_id: int, direction: str) -> Json:
        """direction: up | down."""
        if direction not in {"up", "down"}:
            raise ValueError("direction must be 'up' or 'down'")
        return await get_client().post(f"{HC}/articles/{article_id}/{direction}.json")

    @mcp.tool()
    async def list_article_votes(article_id: int) -> Json:
        return await get_client().list(f"{HC}/articles/{article_id}/votes.json", "votes")

    # ------------------------------------------------- categories & sections
    crud(mcp, "help_center_categories", "help_center_category", base=f"{HC}/categories",
         list_key="categories", wrap="category", what="Help Center category",
         create_hint='e.g. {"name":"Billing","description":"...","locale":"en-us"}')
    crud(mcp, "help_center_sections", "help_center_section", base=f"{HC}/sections",
         list_key="sections", wrap="section", ops="lgud", what="Help Center section")

    @mcp.tool()
    async def create_help_center_section_in_category(
        category_id: int, name: str, description: str | None = None, locale: str = "en-us"
    ) -> Json:
        return await get_client().post(
            f"{HC}/categories/{category_id}/sections.json",
            {"section": _clean({"name": name, "description": description, "locale": locale})},
        )

    @mcp.tool()
    async def list_sections_in_category(category_id: int) -> Json:
        return await get_client().list(f"{HC}/categories/{category_id}/sections.json", "sections")

    # ------------------------------------------------------ access / community
    @mcp.tool()
    async def list_user_segments() -> Json:
        return await get_client().list(f"{HC}/user_segments.json", "user_segments")

    @mcp.tool()
    async def list_permission_groups() -> Json:
        return await get_client().list(f"{HC}/permission_groups.json", "permission_groups")

    @mcp.tool()
    async def list_community_topics() -> Json:
        return await get_client().list(f"{HC}/community/topics.json", "topics")

    @mcp.tool()
    async def list_community_posts(topic_id: int | None = None, page_size: int = 100) -> Json:
        path = f"{HC}/community/topics/{topic_id}/posts.json" if topic_id else f"{HC}/community/posts.json"
        return await get_client().list(path, "posts", page_size=page_size)

    @mcp.tool()
    async def get_community_post(post_id: int) -> Json:
        return await get_client().get(f"{HC}/community/posts/{post_id}.json")

    @mcp.tool()
    async def list_community_post_comments(post_id: int) -> Json:
        return await get_client().list(f"{HC}/community/posts/{post_id}/comments.json", "comments")
