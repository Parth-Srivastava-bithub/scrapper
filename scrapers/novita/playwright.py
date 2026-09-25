import os
import sys
from pathlib import Path
from time import sleep

# Prevent script directory from shadowing the top-level 'playwright' package when run directly
_current_dir = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _current_dir:
    sys.path.pop(0)

# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

chrome_url = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222")


def parse_gpu_availability(text: str):
    if "Data Center GPU Availability" in text:
        text = text.split("Data Center GPU Availability", 1)[1]

    if "*Volume Name" in text:
        text = text.split("*Volume Name", 1)[0]

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    available = []
    unavailable = []

    current = None

    for line in lines:
        if line == "Available":
            current = "available"
            continue

        if line == "None":
            current = "unavailable"
            continue

        if current == "available":
            available.append(line)

        elif current == "unavailable":
            unavailable.append(line)

    return {"available": available, "unavailable": unavailable}


def scrape_novita_datacenters(cdp_url: str | None = None):
    url = cdp_url or os.getenv("CHROME_CDP_URL", chrome_url)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(url)
        context = browser.contexts[0]

        page = next(
            (pg for pg in context.pages if "novita.ai/gpus-console/storage" in pg.url),
            None,
        )
        if page is None:
            page = context.new_page()
            page.goto("https://novita.ai/gpus-console/storage", wait_until="domcontentloaded", timeout=30000)

        dialog = page.locator('[role="dialog"]')

        cards = page.locator("span.addNetworkVolume_dataCenterItem__lcduA")

        for i in range(cards.count()):
            card = page.locator("span.addNetworkVolume_dataCenterItem__lcduA").nth(i)

            name = card.locator(
                "div.addNetworkVolume_dataCenterName__HSF3V"
            ).inner_text()

            card.click(force=True)

            page.wait_for_timeout(1000)

            if not card.locator("img[src*='checked']").count():
                continue

            parsed = parse_gpu_availability(dialog.inner_text())

            results.append(
                {
                    "cluster": name,
                    "available": parsed["available"],
                    "unavailable": parsed["unavailable"],
                }
            )

    return results


def scrape_novita_datacenters_beta(cdp_url: str = chrome_url):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]

        page = next(
            pg for pg in context.pages if "novita.ai/gpus-console/storage" in pg.url
        )

        dialog = page.locator('[role="dialog"]')
        cards = page.locator("span.addNetworkVolume_dataCenterItem__lcduA")

        for i in range(cards.count()):
            card = page.locator("span.addNetworkVolume_dataCenterItem__lcduA").nth(i)
            card.scroll_into_view_if_needed()

            name = card.locator(
                "div.addNetworkVolume_dataCenterName__HSF3V"
            ).inner_text()

            before = dialog.inner_text()
            card.click()

            try:
                page.wait_for_function(
                    """([selector, previous]) => {
                        const el = document.querySelector(selector);
                        return el && el.innerText !== previous;
                    }""",
                    arg=["[role='dialog']", before],
                    timeout=3000,
                )
            except Exception:
                pass

            parsed = parse_gpu_availability(dialog.inner_text())

            results.append(
                {
                    "cluster": name,
                    "available": parsed["available"],
                    "unavailable": parsed["unavailable"],
                }
            )

            sleep(0.5)

    return results
