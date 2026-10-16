from mcp.server.fastmcp import FastMCP

from . import (
    admin,
    generic,
    groups,
    help_center,
    organizations,
    search,
    tickets,
    users,
)

TOOLSETS = {
    "tickets": tickets,
    "search": search,
    "users": users,
    "organizations": organizations,
    "groups": groups,
    "admin": admin,
    "help_center": help_center,
    "generic": generic,
}


def register_all(mcp: FastMCP, enabled: list[str] | None = None) -> None:
    """Register tool groups. ``enabled`` limits them (default: all)."""
    names = enabled or list(TOOLSETS)
    unknown = set(names) - set(TOOLSETS)
    if unknown:
        raise ValueError(f"Unknown toolsets {sorted(unknown)}; valid: {sorted(TOOLSETS)}")
    for name in names:
        TOOLSETS[name].register(mcp)
