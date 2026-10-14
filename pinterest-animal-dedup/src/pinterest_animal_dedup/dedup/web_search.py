from __future__ import annotations

import base64
import re
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from bs4 import BeautifulSoup

from pinterest_animal_dedup.config import settings
from pinterest_animal_dedup.dedup.platforms import DOMESTIC_PLATFORMS
from pinterest_animal_dedup.http_client import fetch_text, get_client
from pinterest_animal_dedup.models import SearchEvidence


def _decode_bing_ck_url(href: str) -> str:
    if "bing.com/ck/a" not in href:
        return href
    m = re.search(r"[?&]u=([^&]+)", href)
    if not m:
        return href
    raw = unquote(m.group(1))
    if raw.startswith("a1"):
        raw = raw[2:]
    pad = "=" * (-len(raw) % 4)
    try:
        return base64.b64decode(raw + pad).decode("utf-8", errors="ignore")
    except Exception:
        return href


def _parse_ddg_html(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, str]] = []
    for block in soup.select(".result"):
        a = block.select_one("a.result__a")
        if not a:
            continue
        href = a.get("href") or ""
        if "uddg=" in href:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            href = qs.get("uddg", [href])[0]
        title = a.get_text(strip=True)
        snippet_el = block.select_one(".result__snippet")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if href:
            results.append({"url": href, "title": title, "snippet": snippet})
    return results


def _parse_bing_html(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, str]] = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("a")
        if not a:
            continue
        href = _decode_bing_ck_url(a.get("href") or "")
        title = a.get_text(strip=True)
        snippet_el = li.select_one(".b_caption p")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if href:
            results.append({"url": href, "title": title, "snippet": snippet})
    return results


def _searx_json(query: str) -> tuple[list[dict[str, str]], str | None]:
    base = getattr(settings, "searx_url", None) or ""
    if not base:
        return [], "searx_not_configured"
    url = f"{base.rstrip('/')}/search"
    client = get_client()
    try:
        from pinterest_animal_dedup.http_client import _throttle

        _throttle()
        resp = client.get(url, params={"q": query, "format": "json"})
        if resp.status_code != 200:
            return [], f"SearX HTTP {resp.status_code}"
        data = resp.json()
        out = []
        for row in data.get("results") or []:
            if row.get("url"):
                out.append(
                    {
                        "url": row["url"],
                        "title": row.get("title") or "",
                        "snippet": row.get("content") or "",
                    }
                )
        return out, None
    except Exception as exc:
        return [], str(exc)
    finally:
        client.close()


def web_search(query: str) -> tuple[list[dict[str, str]], str | None]:
    """Public web search via allowed HTML/JSON endpoints (no login bypass)."""
    errors: list[str] = []

    # DuckDuckGo HTML with retries on anti-bot 202
    for attempt in range(2):
        status, html, err = fetch_text(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
        if err:
            errors.append(err)
            break
        if status == 200 and html:
            parsed = _parse_ddg_html(html)
            if parsed:
                return parsed, None
            errors.append("ddg_empty")
            break
        if status == 202:
            errors.append(f"DuckDuckGo HTTP {status}")
            if attempt == 0:
                time.sleep(1.5)
                continue
            break
        errors.append(f"DuckDuckGo HTTP {status}")
        break

    # Bing HTML fallback
    status, html, err = fetch_text(f"https://www.bing.com/search?q={quote_plus(query)}")
    if not err and status == 200 and html:
        parsed = _parse_bing_html(html)
        if parsed:
            return parsed, None
        errors.append("bing_empty")
    elif err:
        errors.append(err)
    else:
        errors.append(f"Bing HTTP {status}")

    searx_results, searx_err = _searx_json(query)
    if searx_results:
        return searx_results, None
    if searx_err and searx_err != "searx_not_configured":
        errors.append(searx_err)

    return [], "; ".join(errors) if errors else "no_results"


# Back-compat for discover module
def _duckduckgo_html(query: str) -> tuple[list[dict[str, str]], str | None]:
    return web_search(query)


def search_platform(query: str, platform_key: str) -> SearchEvidence:
    meta = DOMESTIC_PLATFORMS[platform_key]
    site_query = f"site:{meta['site']} {query}"
    results, err = web_search(site_query)
    if err:
        return SearchEvidence(platform=platform_key, query=query, error=err)
    if not results:
        return SearchEvidence(platform=platform_key, query=query, error="no_results")

    domain_hint = meta["domain_hint"]
    for r in results:
        url = r["url"]
        if domain_hint in url.lower() or meta["site"] in url.lower():
            return SearchEvidence(
                platform=platform_key,
                query=query,
                result_url=url,
                title=r.get("title"),
                snippet=r.get("snippet"),
            )
    return SearchEvidence(platform=platform_key, query=query, error="no_on_platform_hits")
