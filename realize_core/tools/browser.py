"""
Browser Agent: Headless Playwright-based browser automation.

Provides tools to navigate, interact with, and extract data from web pages.
Designed for cloud deployment (headless Chromium).

Tools:
- browser_navigate — Go to a URL, return page text + screenshot
- browser_click — Click an element by CSS selector or text
- browser_type — Type text into a form field
- browser_screenshot — Capture the current page state
- browser_extract — Extract text/data from specific elements
- browser_scroll — Scroll the page
"""

import asyncio
import base64
import logging
import os
import time

logger = logging.getLogger(__name__)

BROWSER_HEADLESS = os.environ.get("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.environ.get("BROWSER_TIMEOUT", "30"))
BROWSER_SESSION_TTL = int(os.environ.get("BROWSER_SESSION_TTL", "1800"))  # 30 min default

# Browser context pool: {user_id: BrowserSession}
_sessions: dict[str, "BrowserSession"] = {}


class BrowserSession:
    """Manages a single Playwright browser context for a user."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
        self._initialized = False
        self.created_at: float = time.monotonic()

    async def ensure_started(self):
        if self._initialized and self.page and not self.page.is_closed():
            return
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=BROWSER_HEADLESS,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            self.page = await self.context.new_page()
            self.page.set_default_timeout(BROWSER_TIMEOUT * 1000)
            self._initialized = True
            logger.info("Browser session started")
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        except Exception as e:
            raise RuntimeError(f"Failed to start browser: {str(e)[:200]}")

    async def close(self):
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser session: {e}")
        finally:
            self._initialized = False
            self.page = self.context = self.browser = self._playwright = None


async def _get_session(user_id: str) -> BrowserSession:
    # Close expired sessions (TTL-based cleanup)
    if user_id in _sessions:
        session = _sessions[user_id]
        if time.monotonic() - session.created_at > BROWSER_SESSION_TTL:
            logger.info(f"Browser session for user {user_id} expired (TTL={BROWSER_SESSION_TTL}s), recycling")
            await session.close()
            del _sessions[user_id]
    if user_id not in _sessions:
        _sessions[user_id] = BrowserSession()
    session = _sessions[user_id]
    await session.ensure_started()
    return session


async def close_session(user_id: str):
    if user_id in _sessions:
        await _sessions[user_id].close()
        del _sessions[user_id]


async def cleanup_stale_sessions():
    """Close browser sessions that have exceeded their TTL."""
    now = time.monotonic()
    stale = [uid for uid, s in _sessions.items() if now - s.created_at > BROWSER_SESSION_TTL]
    for uid in stale:
        logger.info(f"Cleaning up stale browser session: {uid}")
        await _sessions[uid].close()
        del _sessions[uid]
    return len(stale)


async def cleanup_all_sessions():
    for uid, session in list(_sessions.items()):
        try:
            await session.close()
        except Exception:
            pass
    _sessions.clear()


# ---------------------------------------------------------------------------
# Tool Functions
# ---------------------------------------------------------------------------


async def browser_navigate(url: str, user_id: str = "0") -> dict:
    # SSRF protection: validate URL before navigation
    from realize_core.tools.web import validate_url

    url_error = validate_url(url)
    if url_error:
        return {"url": url, "error": f"URL blocked: {url_error}"}

    session = await _get_session(user_id)
    navigation_error = None
    try:
        await session.page.goto(url, wait_until="domcontentloaded")
        await session.page.wait_for_load_state("networkidle", timeout=10000)
    except Exception as e:
        navigation_error = str(e)[:200]
        logger.warning(f"Browser navigation partial failure for {url}: {navigation_error}")
    title = await session.page.title()
    text = await session.page.evaluate("""() => {
        const body = document.body;
        if (!body) return '';
        const clone = body.cloneNode(true);
        clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
        return clone.innerText.substring(0, 6000);
    }""")
    screenshot_bytes = await session.page.screenshot(type="jpeg", quality=60)
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    result = {"url": session.page.url, "title": title, "text_content": text[:6000], "screenshot_b64": screenshot_b64}
    if navigation_error:
        result["navigation_warning"] = navigation_error
    return result


async def browser_click(selector: str, user_id: str = "0") -> dict:
    session = await _get_session(user_id)
    try:
        await session.page.click(selector, timeout=BROWSER_TIMEOUT * 1000)
        await asyncio.sleep(1)
        await session.page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception as e:
        return {"clicked": False, "selector": selector, "error": str(e)[:200]}
    return {"clicked": True, "selector": selector, "new_url": session.page.url, "new_title": await session.page.title()}


async def browser_type(selector: str, text: str, press_enter: bool = False, user_id: str = "0") -> dict:
    session = await _get_session(user_id)
    try:
        await session.page.fill(selector, text, timeout=BROWSER_TIMEOUT * 1000)
        if press_enter:
            await session.page.press(selector, "Enter")
            await asyncio.sleep(1)
            await session.page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception as e:
        return {"typed": False, "selector": selector, "error": str(e)[:200]}
    return {"typed": True, "selector": selector, "text": text, "pressed_enter": press_enter}


async def browser_screenshot(user_id: str = "0") -> dict:
    session = await _get_session(user_id)
    screenshot_bytes = await session.page.screenshot(type="jpeg", quality=70, full_page=False)
    return {
        "url": session.page.url,
        "title": await session.page.title(),
        "screenshot_b64": base64.b64encode(screenshot_bytes).decode("utf-8"),
    }


async def browser_extract(selector: str = "body", attribute: str = None, user_id: str = "0") -> dict:
    session = await _get_session(user_id)
    try:
        elements = await session.page.query_selector_all(selector)
        items = []
        for el in elements[:50]:
            if attribute:
                items.append({"value": await el.get_attribute(attribute)})
            else:
                items.append({"text": (await el.inner_text())[:500]})
        return {"selector": selector, "count": len(items), "items": items}
    except Exception as e:
        return {"selector": selector, "error": str(e)[:200]}


async def browser_scroll(direction: str = "down", amount: int = 500, user_id: str = "0") -> dict:
    session = await _get_session(user_id)
    delta = amount if direction == "down" else -amount
    await session.page.mouse.wheel(0, delta)
    await asyncio.sleep(0.5)
    scroll_pos = await session.page.evaluate("window.scrollY")
    return {"scrolled": True, "direction": direction, "scroll_position": scroll_pos}


# ---------------------------------------------------------------------------
# Claude Tool Schemas + Registry
# ---------------------------------------------------------------------------

BROWSER_TOOL_SCHEMAS = [
    {
        "name": "browser_navigate",
        "description": "Navigate the browser to a URL and return the page title, visible text, and a screenshot. Use this to load a web page for interaction. Only http/https URLs allowed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to (must be http:// or https://)."}
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_click",
        "description": "Click an element on the current page. DESTRUCTIVE: may trigger navigation, form submission, or other actions. Use CSS selectors or Playwright text selectors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector (e.g., '#submit-btn') or text selector (e.g., 'text=Submit').",
                }
            },
            "required": ["selector"],
        },
    },
    {
        "name": "browser_type",
        "description": "Type text into a form field on the current page. DESTRUCTIVE: replaces existing field content. Optionally press Enter after typing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the input field (e.g., '#search-input', 'input[name=email]')",
                },
                "text": {"type": "string", "description": "Text to type into the field"},
                "press_enter": {
                    "type": "boolean",
                    "description": "Press Enter after typing (default: false)",
                    "default": False,
                },
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a JPEG screenshot of the current browser viewport. Use this to see the current state of the page.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "browser_extract",
        "description": "Extract text content or HTML attributes from elements matching a CSS selector. Returns up to 50 matching elements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector (default: 'body')", "default": "body"},
                "attribute": {
                    "type": "string",
                    "description": "HTML attribute to extract (e.g., 'href', 'src'). Omit to get text content.",
                },
            },
        },
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the current page up or down by a specified pixel amount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Scroll direction (default: 'down')",
                    "default": "down",
                },
                "amount": {"type": "integer", "description": "Pixels to scroll (default: 500)", "default": 500},
            },
        },
    },
]

BROWSER_WRITE_TOOLS = {"browser_click", "browser_type"}
BROWSER_READ_TOOLS = {"browser_navigate", "browser_screenshot", "browser_extract", "browser_scroll"}

TOOL_FUNCTIONS = {
    "browser_navigate": browser_navigate,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_screenshot": browser_screenshot,
    "browser_extract": browser_extract,
    "browser_scroll": browser_scroll,
}
