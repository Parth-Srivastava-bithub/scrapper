import os
import re
import sys
from pathlib import Path

# Prevent script directory from shadowing the top-level 'playwright' package when run directly
_current_dir = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _current_dir:
    sys.path.pop(0)

from playwright.sync_api import sync_playwright
from rapidfuzz import fuzz
from rich import print

chrome_url = os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222")


def runpod_scrape_runpod(cdp_url: str | None = None):
    url = cdp_url or os.getenv("CHROME_CDP_URL", chrome_url)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(url)
        context = browser.contexts[0]

        page = None
        for pg in context.pages:
            if "console.runpod.io/deploy" in pg.url:
                page = pg
                break

        if page is None:
            page = context.new_page()
            page.goto("https://console.runpod.io/deploy", wait_until="domcontentloaded", timeout=45000)

        gpu_names = [
            "H100 SXM",
            "RTX PRO 6000",
            "H200 SXM",
            "B200",
            "RTX 4000 Ada",
            "RTX 4090",
            "RTX PRO 4000",
            "RTX 5090",
            "RTX PRO 4500",
            "L40S",
            "H100 PCIe",
            "H100 NVL",
            "RTX PRO 6000 WK",
            "H200 NVL",
            "B300",
            "RTX 2000 Ada",
            "RTX A4000",
            "RTX A4500",
            "RTX 3090",
            "L4",
            "RTX A5000",
            "A40",
            "L40",
            "RTX 6000 Ada",
            "RTX A6000",
            "A100 PCIe",
            "A100 SXM",
            "MI300X",
        ]

        # Wait for dynamic GPU cards to render in the DOM (up to 15 seconds)
        body = ""
        for _ in range(15):
            try:
                body = page.locator("body").inner_text()
                if any(gpu in body for gpu in gpu_names) or "$/hr" in body:
                    break
            except Exception:
                pass
            page.wait_for_timeout(1000)

        rows = []

        for gpu in gpu_names:
            idx = body.find(gpu)
            if idx == -1:
                continue

            chunk = body[idx : idx + 400]

            price = re.search(r"\$([\d.]+)/hr", chunk)
            vram = re.search(r"(\d+)\s*GB VRAM", chunk)
            max_count = re.search(r"(\d+)\s*max", chunk)
            ram = re.search(r"(\d+)\s*GB RAM", chunk)
            vcpu = re.search(r"(\d+)\s*vCPU", chunk)
            availability = re.search(
                r"\b(High|Medium|Low|Unavailable)\b", chunk, re.IGNORECASE
            )
            rows.append(
                {
                    "gpu_name": gpu,
                    "hourly_price": float(price.group(1)) if price else None,
                    "vram_gb": int(vram.group(1)) if vram else None,
                    "max": int(max_count.group(1)) if max_count else None,
                    "ram_gb": int(ram.group(1)) if ram else None,
                    "vcpu": int(vcpu.group(1)) if vcpu else None,
                    "availability": (
                        availability.group(1).lower() if availability else None
                    ),
                }
            )

        print(f"Scraped {len(rows)} GPU entries from RunPod web console.")
        return rows


def normalize_gpu_name(name: str) -> str:
    name = name.upper()

    replacements = [
        "NVIDIA",
        "TESLA",
        "GENERATION",
        "BLACKWELL",
        "SERVER EDITION",
        "WORKSTATION EDITION",
        "MAX-Q",
        "MAXQ",
    ]

    for r in replacements:
        name = name.replace(r, "")

    name = " ".join(name.split())
    return name.strip()


def match_gpu(playwright_gpu, graphql_gpus):
    best = None
    best_score = -1

    p_name = normalize_gpu_name(playwright_gpu["gpu_name"])

    for gpu in graphql_gpus:
        g_name = normalize_gpu_name(gpu["gpu_name"])

        score = fuzz.ratio(p_name, g_name)

        # Bonus if VRAM matches
        if playwright_gpu.get("vram_gb") is not None and gpu.get(
            "vram_gb"
        ) == playwright_gpu.get("vram_gb"):
            score += 15

        # Bonus if max gpu matches
        if playwright_gpu.get("max") is not None and gpu.get(
            "gpu_count"
        ) == playwright_gpu.get("max"):
            score += 10

        if score > best_score:
            best_score = score
            best = gpu

    return best, best_score


def runpod_merge(playwright_data, graphql_data):
    merged = []

    for pw_gpu in playwright_data:
        gpu, score = match_gpu(pw_gpu, graphql_data)

        if score < 85:
            print(f"❌ No match: {pw_gpu['gpu_name']}")
            continue

        print(f"✅ {pw_gpu['gpu_name']} -> {gpu['gpu_name']} ({score:.1f})")

        merged.append(
            {
                **gpu,
                "ram_gb": pw_gpu["ram_gb"],
                "cpu": pw_gpu["vcpu"],
                "gpu_count": pw_gpu["max"],
                "availability": pw_gpu["availability"] or gpu["availability"],
            }
        )

    return merged
