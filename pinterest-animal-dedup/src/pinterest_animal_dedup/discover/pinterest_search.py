from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from pinterest_animal_dedup.http_client import fetch_text, get_client
from pinterest_animal_dedup.models import PinMediaType, PinterestPin


def _parse_pws_json(html: str) -> dict[str, Any] | None:
    """Extract embedded Pinterest bootstrap JSON when publicly served."""
    patterns = [
        r'<script[^>]*id="__PWS_INITIAL_PROPS__"[^>]*>(.*?)</script>',
        r'<script[^>]*id="__PWS_DATA__"[^>]*>(.*?)</script>',
        r'<script[^>]*id="__PWS_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
        r'window\.__PWS_INITIAL_PROPS__\s*=\s*(\{.*?\});',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if not m:
            continue
        raw = m.group(1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    # Fallback: any large JSON blob mentioning pin_id
    for script in re.findall(r"<script[^>]*type=\"application/json\"[^>]*>(.*?)</script>", html):
        if "pin_id" not in script and "pins" not in script:
            continue
        try:
            data = json.loads(script)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def _walk_pins(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if "id" in node and ("grid_title" in node or "title" in node or "images" in node):
            pid = str(node.get("id", ""))
            if pid.isdigit() and len(pid) >= 10:
                found.append(node)
        for v in node.values():
            _walk_pins(v, found)
    elif isinstance(node, list):
        for item in node:
            _walk_pins(item, found)


def _media_type_from_pin(raw: dict[str, Any]) -> PinMediaType:
    if raw.get("is_video") or raw.get("videos") or raw.get("story_pin_data"):
        return PinMediaType.VIDEO
    if raw.get("is_gif") or str(raw.get("type", "")).lower() == "gif":
        return PinMediaType.GIF
    if raw.get("story_pin_data"):
        return PinMediaType.STORY
    if raw.get("images"):
        return PinMediaType.IMAGE
    return PinMediaType.UNKNOWN


def _thumbnail(raw: dict[str, Any]) -> str | None:
    images = raw.get("images") or {}
    if isinstance(images, dict):
        for key in ("736x", "orig", "474x", "236x"):
            entry = images.get(key)
            if isinstance(entry, dict) and entry.get("url"):
                return entry["url"]
    return None


def _pin_url(pin_id: str, slug: str | None = None) -> str:
    return f"https://www.pinterest.com/pin/{pin_id}/"


def extract_pin_id_from_url(url: str) -> str | None:
    m = re.search(r"/pin/(?:[^/]+--)?(\d{10,20})/?", url)
    if m:
        return m.group(1)
    m = re.search(r"/pin/(\d{10,20})", url)
    return m.group(1) if m else None


def _canonical_pin_url(url: str) -> str:
    pin_id = extract_pin_id_from_url(url)
    if pin_id:
        return _pin_url(pin_id)
    return url.split("?")[0]


def parse_pin_page_html(html: str, pin_id: str, source_query: str, page_url: str) -> PinterestPin:
    soup = BeautifulSoup(html, "lxml")
    title = ""
    desc = ""
    thumb = None
    for prop, attr in (("og:title", "title"), ("og:description", "description"), ("og:image", "thumb")):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            val = tag["content"].strip()
            if attr == "title":
                title = val
            elif attr == "description":
                desc = val
            else:
                thumb = val
    media = PinMediaType.UNKNOWN
    lower = html.lower()
    if '"is_video":true' in lower or "video.pinimg.com" in lower or "og:video" in lower:
        media = PinMediaType.VIDEO
    elif ".gif" in (thumb or "").lower():
        media = PinMediaType.GIF
    elif thumb:
        media = PinMediaType.IMAGE
    return PinterestPin(
        pin_id=pin_id,
        url=_canonical_pin_url(page_url),
        title=title,
        description=desc,
        media_type=media,
        thumbnail_url=thumb,
        source_query=source_query,
        raw={"id": pin_id, "is_video": media == PinMediaType.VIDEO},
    )


def _normalize_pin(raw: dict[str, Any], source_query: str) -> PinterestPin | None:
    pin_id = str(raw.get("id", "")).strip()
    if not pin_id.isdigit():
        return None
    title = (raw.get("grid_title") or raw.get("title") or raw.get("seo_title") or "").strip()
    desc = (raw.get("description") or raw.get("grid_description") or "").strip()
    slug = raw.get("link") or raw.get("seo_url")
    video = None
    videos = raw.get("videos") or {}
    if isinstance(videos, dict):
        vlist = videos.get("video_list") or videos.get("videos") or {}
        if isinstance(vlist, dict):
            for quality in ("V_720P", "V_HLSV4", "V_480P", "V_EXP7"):
                entry = vlist.get(quality)
                if isinstance(entry, dict) and entry.get("url"):
                    video = entry["url"]
                    break
    tags: list[str] = []
    for t in raw.get("hashtags") or []:
        if isinstance(t, str):
            tags.append(t.lstrip("#"))
        elif isinstance(t, dict) and t.get("name"):
            tags.append(str(t["name"]).lstrip("#"))
    return PinterestPin(
        pin_id=pin_id,
        url=_pin_url(pin_id, str(slug) if slug else None),
        title=title,
        description=desc,
        media_type=_media_type_from_pin(raw),
        thumbnail_url=_thumbnail(raw),
        video_url=video,
        source_query=source_query,
        tags=tags,
        raw={"id": pin_id, "is_video": bool(video or raw.get("is_video"))},
    )


def search_pins(query: str, limit: int = 12) -> tuple[list[PinterestPin], list[str], str | None]:
    """
    Search Pinterest via public search page HTML (logged-out accessible when Pinterest allows).
    Returns pins, related_terms, error.
    """
    url = f"https://www.pinterest.com/search/pins/?q={quote_plus(query)}"
    status, html, err = fetch_text(url)
    if err:
        return [], [], err
    if status in (401, 403):
        return [], [], f"Pinterest returned HTTP {status} (access blocked; no bypass attempted)"
    if status != 200 or not html:
        return [], [], f"Pinterest returned HTTP {status}"

    related: list[str] = []
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href*="/search/pins/?q="]'):
        href = a.get("href") or ""
        m = re.search(r"[?&]q=([^&]+)", href)
        if m:
            term = m.group(1).replace("+", " ")
            if term.lower() not in {query.lower()} and term not in related:
                related.append(term)

    data = _parse_pws_json(html)
    raw_pins: list[dict[str, Any]] = []
    if data:
        _walk_pins(data, raw_pins)

    # Dedupe by id
    seen: set[str] = set()
    pins: list[PinterestPin] = []
    for raw in raw_pins:
        pin = _normalize_pin(raw, query)
        if not pin or pin.pin_id in seen:
            continue
        seen.add(pin.pin_id)
        pins.append(pin)
        if len(pins) >= limit:
            break

    if not pins:
        for a in soup.select('a[href*="/pin/"]'):
            href = a.get("href") or ""
            pid = extract_pin_id_from_url(href)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            title = (a.get("aria-label") or a.get_text(strip=True) or "")[:200]
            pins.append(
                PinterestPin(
                    pin_id=pid,
                    url=_canonical_pin_url(href),
                    title=title,
                    source_query=query,
                    media_type=PinMediaType.UNKNOWN,
                )
            )
            if len(pins) >= limit:
                break

    if not pins:
        for pid in re.findall(r"/pin/[a-z0-9-]*--(\d{10,20})/", html, flags=re.I):
            if pid in seen:
                continue
            seen.add(pid)
            pins.append(
                PinterestPin(
                    pin_id=pid,
                    url=_pin_url(pid),
                    source_query=query,
                    media_type=PinMediaType.UNKNOWN,
                )
            )
            if len(pins) >= limit:
                break

    if not pins:
        return [], related[:10], "No pins parsed from public Pinterest search HTML"

    return pins, related[:10], None


def enrich_pin_detail(pin: PinterestPin) -> PinterestPin:
    """Fetch public pin page for richer metadata when accessible."""
    status, html, err = fetch_text(pin.url)
    if err or status != 200:
        return pin
    data = _parse_pws_json(html)
    if data:
        raw_pins: list[dict[str, Any]] = []
        _walk_pins(data, raw_pins)
        for raw in raw_pins:
            if str(raw.get("id")) == pin.pin_id:
                enriched = _normalize_pin(raw, pin.source_query)
                if enriched:
                    return enriched
    return parse_pin_page_html(html, pin.pin_id, pin.source_query, pin.url)
