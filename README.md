# Zendesk MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes the Zendesk Support and Help Center
REST APIs (~295 tools): tickets, comments, audits, tags, attachments, search, users, organizations,
groups, views, macros, triggers, automations, SLAs, webhooks, custom objects, CSAT, Help Center and more.
Anything without a dedicated tool is reachable through `zendesk_api_request`.

## Setup

```bash
cp .env.example .env        # fill in ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=src python -m zendesk_mcp
```

Get an API token in Admin Center → Apps and integrations → APIs → Zendesk API.
Alternatively set `ZENDESK_OAUTH_TOKEN`.

## Docker

```bash
docker build -t zendesk-mcp .

# stdio (for Claude Desktop / Claude Code)
docker run -i --rm --env-file .env zendesk-mcp

# HTTP server at http://localhost:8000/mcp
docker compose up --build
```

## Client configuration

Claude Code (stdio via Docker):

```bash
claude mcp add zendesk -- docker run -i --rm --env-file /abs/path/.env zendesk-mcp
```

Claude Desktop / generic `mcp.json`:

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "python",
      "args": ["-m", "zendesk_mcp"],
      "env": {
        "PYTHONPATH": "/abs/path/to/src",
        "ZENDESK_SUBDOMAIN": "yourcompany",
        "ZENDESK_EMAIL": "agent@yourcompany.com",
        "ZENDESK_API_TOKEN": "..."
      }
    }
  }
}
```

## Safety & tuning

| Variable | Effect |
|---|---|
| `ZENDESK_READ_ONLY=true` | Blocks every non-GET request (including `zendesk_api_request`). |
| `ZENDESK_TOOLSETS=tickets,search,users` | Expose only some groups (`tickets, search, users, organizations, groups, admin, help_center, generic`) to save LLM context. |
| `MCP_TRANSPORT` | `stdio` (default), `streamable-http`, or `sse`. |

The HTTP transport has **no authentication of its own** - keep it bound to localhost or put it
behind an authenticating proxy; anyone who can reach it acts with your Zendesk credentials.

429/5xx responses are retried honoring `Retry-After`. Absolute URLs are only followed on your own
Zendesk host.

## Layout

```
src/zendesk_mcp/
  config.py  client.py  server.py
  tools/  tickets.py search.py users.py organizations.py groups.py admin.py help_center.py generic.py
tests/
```

## Tests

```bash
pip install -r requirements-dev.txt && pytest
```
