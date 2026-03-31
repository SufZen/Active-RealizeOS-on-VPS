"""
Web Tools: Search the web and fetch/read web pages.

Two capabilities:
1. web_search — Search the web using Brave Search API
2. web_fetch — Fetch a URL and extract clean readable content
"""

import asyncio
import ipaddress
import logging
import os
import re
import socket
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# ---------------------------------------------------------------------------
# URL Validation (SSRF Protection)
# ---------------------------------------------------------------------------

# Private/reserved IP ranges that should never be accessed by tools
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or reserved."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local or addr.is_multicast
    except ValueError:
        return False


def validate_url(url: str) -> str | None:
    """
    Validate a URL for SSRF safety.

    Returns an error message if the URL is unsafe, None if OK.
    Exported for reuse by browser tools.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    # Scheme check
    if parsed.scheme not in ("http", "https"):
        return f"Blocked URL scheme: {parsed.scheme} (only http/https allowed)"

    hostname = parsed.hostname
    if not hostname:
        return "URL has no hostname"

    # Blocked hostnames
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return f"Blocked hostname: {hostname}"

    # Resolve hostname and check IP
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                return f"Blocked: {hostname} resolves to private/reserved IP {ip_str}"
    except socket.gaierror:
        return f"Cannot resolve hostname: {hostname}"

    return None


_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            headers={"User-Agent": "RealizeOS/1.0"},
        )
    return _http_client


async def close_http_client():
    """Close the global HTTP client. Call during shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def web_search(query: str, count: int = 5, freshness: str = None) -> list[dict]:
    """
    Search the web using Brave Search API.

    Args:
        query: Search query string.
        count: Number of results (1-20, default 5).
        freshness: Optional filter: "pd" (past day), "pw" (week), "pm" (month), "py" (year).

    Returns:
        List of result dicts: {title, url, description, age, extra_snippets}.
    """
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return [{"error": "Brave Search API key not configured. Set BRAVE_API_KEY in .env"}]

    client = _get_http_client()
    params = {"q": query, "count": min(count, 20)}
    if freshness:
        params["freshness"] = freshness

    last_error = None
    for attempt in range(3):
        try:
            resp = await client.get(
                BRAVE_SEARCH_URL,
                params=params,
                headers={"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age", ""),
                        "extra_snippets": item.get("extra_snippets", []),
                    }
                )
            logger.info(f"Web search '{query}': {len(results)} results")
            return results
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code in (429, 503) and attempt < 2:
                wait = (2**attempt) * 1.0
                logger.warning(f"Brave Search {e.response.status_code}, retrying in {wait}s (attempt {attempt + 1}/3)")
                await asyncio.sleep(wait)
                continue
            logger.error(f"Brave Search HTTP error: {e.response.status_code}")
            return [{"error": f"Search API error: {e.response.status_code}"}]
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return [{"error": f"Search failed: {str(e)[:200]}"}]

    return [{"error": f"Search failed after 3 attempts: {str(last_error)[:200]}"}]


# ---------------------------------------------------------------------------
# Web Fetch
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\n{3,}")


def _simple_html_to_text(html: str) -> str:
    """Basic HTML-to-text fallback when trafilatura is not available."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')
    text = _WHITESPACE_RE.sub("\n\n", text).strip()
    return text


async def web_fetch(url: str, max_chars: int = 8000, extract_mode: str = "auto") -> dict:
    """
    Fetch a URL and return its content as clean readable text.

    Args:
        url: The URL to fetch.
        max_chars: Maximum characters to return (default 8000).
        extract_mode: "auto", "trafilatura", "simple", or "raw".

    Returns:
        Dict with {url, title, content, content_length, truncated}.
    """
    # SSRF protection: validate URL before fetching
    url_error = validate_url(url)
    if url_error:
        return {"url": url, "error": f"URL blocked: {url_error}"}

    client = _get_http_client()
    try:
        resp = await client.get(
            url,
            headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"},
        )
        resp.raise_for_status()
        html = resp.text
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        content = ""
        if extract_mode in ("auto", "trafilatura"):
            try:
                import trafilatura

                content = (
                    trafilatura.extract(
                        html,
                        include_links=True,
                        include_tables=True,
                        favor_recall=True,
                        url=url,
                    )
                    or ""
                )
            except ImportError:
                content = _simple_html_to_text(html) if extract_mode == "auto" else ""
            except Exception:
                content = _simple_html_to_text(html)
        elif extract_mode == "simple":
            content = _simple_html_to_text(html)
        elif extract_mode == "raw":
            content = html
        else:
            content = _simple_html_to_text(html)
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars] + "\n\n[...truncated]"
        return {"url": url, "title": title, "content": content, "content_length": len(content), "truncated": truncated}
    except httpx.HTTPStatusError as e:
        return {"url": url, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"url": url, "error": f"Fetch failed: {str(e)[:200]}"}
