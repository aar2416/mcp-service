from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    subdomain: str
    email: str | None
    api_token: str | None
    oauth_token: str | None
    read_only: bool
    timeout: float
    max_retries: int

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.zendesk.com/api/v2"

    @classmethod
    def from_env(cls) -> "Settings":
        subdomain = os.environ.get("ZENDESK_SUBDOMAIN", "").strip()
        # Accept a pasted full host like "https://acme.zendesk.com"
        subdomain = subdomain.removeprefix("https://").split(".zendesk.com")[0].strip("/")
        email = os.environ.get("ZENDESK_EMAIL") or None
        api_token = os.environ.get("ZENDESK_API_TOKEN") or None
        oauth = os.environ.get("ZENDESK_OAUTH_TOKEN") or None

        if not subdomain:
            raise RuntimeError("ZENDESK_SUBDOMAIN is required")
        if not oauth and not (email and api_token):
            raise RuntimeError(
                "Set ZENDESK_OAUTH_TOKEN, or both ZENDESK_EMAIL and ZENDESK_API_TOKEN"
            )
        return cls(
            subdomain=subdomain,
            email=email,
            api_token=api_token,
            oauth_token=oauth,
            read_only=_bool("ZENDESK_READ_ONLY"),
            timeout=float(os.environ.get("ZENDESK_TIMEOUT", "30")),
            max_retries=int(os.environ.get("ZENDESK_MAX_RETRIES", "3")),
        )
