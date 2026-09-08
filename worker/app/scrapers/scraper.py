"""
Async Playwright scraper. Handles dynamic (JS-rendered) storefronts by
waiting on network idle rather than fixed sleeps, rotates through a proxy
pool round-robin, and falls back to a headful browser (harder for basic
bot-detection to flag) after headless attempts are exhausted.

This is written against generic, common e-commerce DOM patterns (JSON-LD
`price` field first, then a set of CSS selector fallbacks) since "the"
target storefront isn't fixed — swap `PRICE_SELECTORS` / `_extract_price`
for site-specific logic once you know which storefronts you're targeting.
"""
import asyncio
import itertools
import json
import logging
import re
from dataclasses import dataclass

from playwright.async_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, async_playwright

from app.core.config import get_settings

logger = logging.getLogger("pricepulse.worker.scraper")
settings = get_settings()

PRICE_SELECTORS = [
    "[itemprop='price']",
    "[data-testid='product-price']",
    ".price .a-offscreen",  # amazon-style
    ".notranslate",
    "span.price",
    ".price-tag",
]
PROMO_SELECTORS = [
    "[data-testid='promo-details']",
    ".promo-details",
    ".bank-offer",
    ".offers-list",
]
PRICE_PATTERN = re.compile(r"[\d,]+\.?\d*")


@dataclass
class ScrapeResult:
    product_title: str | None
    price_amount: float | None
    currency: str
    in_stock: bool
    promo_text: str | None


class ScrapeError(Exception):
    """Raised after all retries/fallbacks are exhausted for a given URL."""


class PlaywrightScraper:
    """
    One instance is created per worker process and reused across messages —
    launching a fresh browser per scrape would dominate latency. Call
    `start()` once at worker boot and `stop()` at shutdown.
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._proxy_cycle = itertools.cycle(settings.proxy_list) if settings.proxy_list else None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=settings.SCRAPER_HEADLESS)
        logger.info("Playwright browser launched (headless=%s)", settings.SCRAPER_HEADLESS)

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        logger.info("Playwright browser closed")

    def _next_proxy(self) -> str | None:
        return next(self._proxy_cycle) if self._proxy_cycle else None

    async def scrape(self, product_url: str) -> ScrapeResult:
        """
        Retries with exponential backoff, rotating proxy each attempt. The
        final attempt forces a headful context regardless of the configured
        default, since some storefronts specifically challenge headless
        fingerprints.
        """
        last_error: Exception | None = None
        for attempt in range(1, settings.SCRAPER_MAX_RETRIES + 1):
            force_headful = attempt == settings.SCRAPER_MAX_RETRIES
            try:
                return await self._attempt_scrape(product_url, force_headful=force_headful)
            except (PlaywrightTimeoutError, ScrapeError) as exc:
                last_error = exc
                logger.warning(
                    "Scrape attempt %s/%s failed for %s: %s",
                    attempt, settings.SCRAPER_MAX_RETRIES, product_url, exc,
                )
                await asyncio.sleep(settings.SCRAPER_RETRY_BACKOFF_SECONDS * attempt)

        raise ScrapeError(f"All {settings.SCRAPER_MAX_RETRIES} attempts failed for {product_url}") from last_error

    async def _attempt_scrape(self, product_url: str, force_headful: bool) -> ScrapeResult:
        if self._browser is None:
            raise RuntimeError("Scraper used before start() was called")

        proxy = self._next_proxy()
        context_kwargs: dict = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "viewport": {"width": 1366, "height": 900},
        }
        if proxy:
            context_kwargs["proxy"] = {"server": proxy}

        browser = self._browser
        temp_browser: Browser | None = None
        if force_headful and settings.SCRAPER_HEADLESS:
            # Launch a one-off headful browser just for this final attempt.
            temp_browser = await self._playwright.chromium.launch(headless=False)
            browser = temp_browser

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        try:
            await page.goto(
                product_url,
                timeout=settings.SCRAPER_NAV_TIMEOUT_MS,
                wait_until="domcontentloaded",
            )
            await page.wait_for_load_state("networkidle", timeout=settings.SCRAPER_NAV_TIMEOUT_MS)
            return await self._extract(page)
        finally:
            await context.close()
            if temp_browser is not None:
                await temp_browser.close()

    async def _extract(self, page: Page) -> ScrapeResult:
        title = await self._extract_title(page)
        price_amount, currency = await self._extract_price(page)
        promo_text = await self._extract_promo(page)
        in_stock = price_amount is not None

        if price_amount is None:
            raise ScrapeError("Could not locate a price on the page with any known selector")

        return ScrapeResult(
            product_title=title,
            price_amount=price_amount,
            currency=currency,
            in_stock=in_stock,
            promo_text=promo_text,
        )

    @staticmethod
    async def _extract_title(page: Page) -> str | None:
        try:
            title = await page.title()
            return title.strip()[:512] if title else None
        except PlaywrightTimeoutError:
            return None

    @staticmethod
    async def _extract_price(page: Page) -> tuple[float | None, str]:
        # Prefer structured JSON-LD data — it's the least brittle source.
        try:
            ld_json_handles = await page.query_selector_all("script[type='application/ld+json']")
            for handle in ld_json_handles:
                raw = await handle.text_content()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                candidates = data if isinstance(data, list) else [data]
                for candidate in candidates:
                    offers = candidate.get("offers") if isinstance(candidate, dict) else None
                    if isinstance(offers, dict) and offers.get("price"):
                        currency = offers.get("priceCurrency", "INR")
                        return float(offers["price"]), currency
        except Exception:  # noqa: BLE001 - JSON-LD is best-effort, fall through to selectors
            pass

        for selector in PRICE_SELECTORS:
            element = await page.query_selector(selector)
            if element is None:
                continue
            raw_text = await element.text_content()
            if not raw_text:
                continue
            match = PRICE_PATTERN.search(raw_text.replace(",", ""))
            if match:
                return float(match.group()), "INR"

        return None, "INR"

    @staticmethod
    async def _extract_promo(page: Page) -> str | None:
        for selector in PROMO_SELECTORS:
            element = await page.query_selector(selector)
            if element is None:
                continue
            text = await element.text_content()
            if text and text.strip():
                return text.strip()[:2000]
        return None
