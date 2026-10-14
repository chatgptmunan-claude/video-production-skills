from __future__ import annotations

from pinterest_animal_dedup.dedup.web_search import _duckduckgo_html
from pinterest_animal_dedup.discover.pinterest_search import (
    _canonical_pin_url,
    enrich_pin_detail,
    extract_pin_id_from_url,
)
from pinterest_animal_dedup.models import PinterestPin


def search_pins_public_index(query: str, limit: int = 12) -> tuple[list[PinterestPin], str | None]:
    """
    Discover real Pinterest pin URLs via public web search (site:pinterest.com/pin).
    Used when Pinterest search HTML is client-rendered without pin payloads.
    """
    ddg_query = f"site:pinterest.com/pin {query}"
    results, err = _duckduckgo_html(ddg_query)
    if err:
        return [], err
    pins: list[PinterestPin] = []
    seen: set[str] = set()
    for row in results:
        url = row.get("url") or ""
        if "pinterest.com/pin/" not in url.lower():
            continue
        pin_id = extract_pin_id_from_url(url)
        if not pin_id or pin_id in seen:
            continue
        seen.add(pin_id)
        title = (row.get("title") or "")[:300]
        snippet = (row.get("snippet") or "")[:500]
        pins.append(
            PinterestPin(
                pin_id=pin_id,
                url=_canonical_pin_url(url),
                title=title,
                description=snippet,
                source_query=query,
            )
        )
        if len(pins) >= limit:
            break
    if not pins:
        return [], "no_pins_in_public_index"
    return pins, None
