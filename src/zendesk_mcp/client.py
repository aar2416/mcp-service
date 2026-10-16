from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import Settings

Json = dict[str, Any]
_RETRY_STATUS = {429, 502, 503, 504}
MAX_PAGES_CAP = 50


class ZendeskError(Exception):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"Zendesk API error {status}: {message}")
        self.status = status
        self.body = body


class ZendeskClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        headers = {"Accept": "application/json", "User-Agent": "zendesk-mcp/1.0"}
        auth: httpx.Auth | None = None
        if settings.oauth_token:
            headers["Authorization"] = f"Bearer {settings.oauth_token}"
        else:
            auth = httpx.BasicAuth(f"{settings.email}/token", settings.api_token or "")
        self._origin = f"https://{settings.subdomain}.zendesk.com"
        self._http = httpx.AsyncClient(
            base_url=settings.base_url,
            headers=headers,
            auth=auth,
            timeout=settings.timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Json | None = None,
        json: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        method = method.upper()
        if self.settings.read_only and method not in {"GET", "HEAD"}:
            raise ZendeskError(403, "Server is in read-only mode (ZENDESK_READ_ONLY=true)")

        # Absolute URLs (pagination links) are used as-is but must stay on this account.
        if path.startswith("http"):
            if not path.startswith(self._origin + "/"):
                raise ZendeskError(400, "Refusing to call a host outside this Zendesk account")
            target = path
        else:
            target = "/api/v2/" + path.lstrip("/")
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        attempt = 0
        while True:
            resp = await self._http.request(
                method,
                target if target.startswith("http") else self._origin + target,
                params=params,
                json=json,
                content=content,
                headers=headers,
            )
            retryable = resp.status_code in _RETRY_STATUS and (
                resp.status_code == 429 or method == "GET"
            )
            if retryable and attempt < self.settings.max_retries:
                attempt += 1
                try:
                    delay = float(resp.headers.get("Retry-After", 2**attempt))
                except ValueError:
                    delay = 2**attempt
                await asyncio.sleep(min(delay, 60))
                continue
            break

        if resp.status_code == 204 or not resp.content:
            return {"status": "success", "http_status": resp.status_code}
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            msg = ""
            if isinstance(data, dict):
                msg = str(data.get("description") or data.get("error") or data.get("message") or "")
                if data.get("details"):
                    msg += f" details={data['details']}"
            raise ZendeskError(resp.status_code, msg or resp.reason_phrase, data)
        return data

    async def get(self, path: str, params: Json | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, body: Any = None, params: Json | None = None) -> Any:
        return await self.request("POST", path, json=body, params=params)

    async def put(self, path: str, body: Any = None, params: Json | None = None) -> Any:
        return await self.request("PUT", path, json=body, params=params)

    async def patch(self, path: str, body: Any = None) -> Any:
        return await self.request("PATCH", path, json=body)

    async def delete(self, path: str, params: Json | None = None, body: Any = None) -> Any:
        return await self.request("DELETE", path, params=params, json=body)

    async def list(
        self,
        path: str,
        key: str,
        *,
        params: Json | None = None,
        page_size: int = 100,
        max_pages: int = 1,
        page: int | None = None,
    ) -> Json:
        """Fetch up to ``max_pages`` pages and merge the ``key`` arrays.

        Handles both offset (``next_page``) and cursor (``links.next``) pagination.
        """
        max_pages = max(1, min(max_pages, MAX_PAGES_CAP))
        q: Json | None = {"per_page": max(1, min(page_size, 100)), **(params or {})}
        if page:
            q["page"] = page
        items: list[Any] = []
        url: str | None = path
        has_more = False
        for _ in range(max_pages):
            data = await self.get(url, q)
            q = None  # next URLs already carry the query string
            items.extend(data.get(key, []))
            url = data.get("next_page")
            if not url and (data.get("meta") or {}).get("has_more"):
                url = (data.get("links") or {}).get("next")
            has_more = bool(url)
            if not url:
                break
        out: Json = {"count": len(items), key: items, "has_more": has_more}
        if has_more:
            out["next_page"] = url
        return out


_client: ZendeskClient | None = None


def get_client() -> ZendeskClient:
    global _client
    if _client is None:
        _client = ZendeskClient(Settings.from_env())
    return _client


def set_client(client: ZendeskClient | None) -> None:
    """Test hook."""
    global _client
    _client = client
