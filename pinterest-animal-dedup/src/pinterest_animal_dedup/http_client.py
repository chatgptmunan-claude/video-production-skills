from __future__ import annotations

import time
from typing import Any

import httpx

from pinterest_animal_dedup.config import settings

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = settings.request_delay_seconds - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def get_client() -> httpx.Client:
    return httpx.Client(
        timeout=settings.http_timeout,
        headers={"User-Agent": settings.http_user_agent},
        follow_redirects=True,
    )


def fetch_text(url: str, client: httpx.Client | None = None) -> tuple[int, str, str | None]:
    """Returns status_code, body, error_message."""
    own = client is None
    if own:
        client = get_client()
    try:
        _throttle()
        resp = client.get(url)
        return resp.status_code, resp.text, None
    except httpx.HTTPError as exc:
        return 0, "", str(exc)
    finally:
        if own:
            client.close()


def fetch_bytes(url: str, client: httpx.Client | None = None) -> tuple[int, bytes, str | None]:
    own = client is None
    if own:
        client = get_client()
    try:
        _throttle()
        resp = client.get(url)
        if resp.status_code != 200:
            return resp.status_code, b"", f"HTTP {resp.status_code}"
        return 200, resp.content, None
    except httpx.HTTPError as exc:
        return 0, b"", str(exc)
    finally:
        if own:
            client.close()
