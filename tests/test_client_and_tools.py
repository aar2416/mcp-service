import json

import httpx
import pytest
import respx

from zendesk_mcp.client import ZendeskClient, ZendeskError, set_client
from zendesk_mcp.config import Settings
from zendesk_mcp.server import create_server

BASE = "https://acme.zendesk.com/api/v2"


def make_client(read_only=False):
    return ZendeskClient(Settings("acme", "a@b.com", "tok", None, read_only, 5, 1))


@pytest.fixture(autouse=True)
def client():
    c = make_client()
    set_client(c)
    yield c
    set_client(None)


@pytest.mark.asyncio
async def test_all_tools_register_with_unique_names():
    tools = await create_server().list_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names))
    assert len(names) > 250
    subset = [t.name for t in await create_server(toolsets=["tickets"]).list_tools()]
    assert "create_ticket" in subset and "list_views" not in subset
    for expected in ("create_ticket", "update_ticket", "search", "list_views", "list_articles",
                     "create_webhook", "zendesk_api_request"):
        assert expected in names


@pytest.mark.asyncio
@respx.mock
async def test_create_ticket_payload_and_auth():
    route = respx.post(f"{BASE}/tickets.json").mock(
        return_value=httpx.Response(201, json={"ticket": {"id": 1}})
    )
    out = await create_server().call_tool(
        "create_ticket",
        {"subject": "Hi", "comment_body": "help", "requester_email": "u@x.com", "priority": "high"},
    )
    req = route.calls[0].request
    assert req.headers["authorization"].startswith("Basic ")
    body = json.loads(req.content)["ticket"]
    assert body["comment"] == {"body": "help", "public": True}
    assert body["requester"] == {"email": "u@x.com"}
    assert body["priority"] == "high"
    assert out


@pytest.mark.asyncio
@respx.mock
async def test_pagination_follows_next_page(client):
    respx.get(f"{BASE}/tickets.json", params={"page": "2"}).mock(
        return_value=httpx.Response(200, json={"tickets": [{"id": 2}], "next_page": None})
    )
    respx.get(f"{BASE}/tickets.json").mock(
        return_value=httpx.Response(200, json={
            "tickets": [{"id": 1}], "next_page": f"{BASE}/tickets.json?page=2"})
    )
    res = await client.list("/tickets.json", "tickets", max_pages=5)
    assert [t["id"] for t in res["tickets"]] == [1, 2]
    assert res["has_more"] is False


@pytest.mark.asyncio
@respx.mock
async def test_error_and_retry_on_429(client):
    respx.get(f"{BASE}/tickets/9.json").mock(side_effect=[
        httpx.Response(429, headers={"Retry-After": "0"}, json={}),
        httpx.Response(404, json={"error": "RecordNotFound", "description": "Not found"}),
    ])
    with pytest.raises(ZendeskError) as e:
        await client.get("/tickets/9.json")
    assert e.value.status == 404


@pytest.mark.asyncio
async def test_read_only_blocks_writes():
    c = make_client(read_only=True)
    with pytest.raises(ZendeskError):
        await c.post("/tickets.json", {"ticket": {}})


@pytest.mark.asyncio
async def test_rejects_foreign_host(client):
    with pytest.raises(ZendeskError):
        await client.get("https://evil.example.com/api/v2/users.json")
