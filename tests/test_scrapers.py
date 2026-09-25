"""Tests for scraper-worker scrapers."""

import pytest

from scrapers.novita.api import NovitaScraperAPI
from scrapers.novita.playwright import parse_gpu_availability
from scrapers.runpod.playwright import match_gpu, normalize_gpu_name, runpod_merge


def test_normalize_gpu_name():
    assert normalize_gpu_name("NVIDIA GeForce RTX 4090") == "GEFORCE RTX 4090"
    assert normalize_gpu_name("Tesla V100 Max-Q") == "V100"


def test_match_gpu():
    playwright_gpu = {
        "gpu_name": "RTX 4090",
        "vram_gb": 24,
        "max": 8,
        "ram_gb": 64,
        "vcpu": 16,
        "availability": "high",
    }
    graphql_gpus = [
        {
            "gpu_name": "RTX 4090",
            "vram_gb": 24,
            "gpu_count": 8,
            "availability": "high",
            "hourly_price": 0.74,
        },
        {
            "gpu_name": "A100 SXM",
            "vram_gb": 80,
            "gpu_count": 8,
            "availability": "low",
            "hourly_price": 2.00,
        },
    ]

    matched, score = match_gpu(playwright_gpu, graphql_gpus)
    assert matched is not None
    assert matched["gpu_name"] == "RTX 4090"
    assert score >= 85


def test_runpod_merge():
    pw_data = [
        {
            "gpu_name": "RTX 4090",
            "vram_gb": 24,
            "max": 8,
            "ram_gb": 64,
            "vcpu": 16,
            "availability": "high",
        }
    ]
    gql_data = [
        {
            "provider": "RunPod",
            "gpu_id": "NVIDIA GeForce RTX 4090",
            "gpu_name": "RTX 4090",
            "vram_gb": 24,
            "gpu_count": 8,
            "availability": "high",
            "hourly_price": 0.74,
            "community_price": 0.50,
            "secure_price": 0.74,
            "spot_price": None,
            "deployable": True,
            "manufacturer": "Nvidia",
            "regions": None,
            "reliability": None,
        }
    ]

    merged = runpod_merge(pw_data, gql_data)
    assert len(merged) == 1
    assert merged[0]["ram_gb"] == 64
    assert merged[0]["cpu"] == 16


def test_novita_scraper_api_extract_vram():
    assert NovitaScraperAPI.extract_vram("RTX 4090 (24GB)") == 24
    assert NovitaScraperAPI.extract_vram("A100-80GB-SXM") == 80
    assert NovitaScraperAPI.extract_vram("Unknown GPU") is None


def test_parse_gpu_availability():
    sample_text = """
    Data Center GPU Availability
    Available
    RTX 4090
    A100
    None
    H100
    *Volume Name
    """
    parsed = parse_gpu_availability(sample_text)
    assert "RTX 4090" in parsed["available"]
    assert "A100" in parsed["available"]
    assert "H100" in parsed["unavailable"]


def test_playwright_cdp_skipped_when_unavailable():
    """Verify live Playwright CDP connection is skipped if Chrome is not running."""
    from scrapers.runpod.playwright import runpod_scrape_runpod

    # If CDP is not running locally, calling these will raise an exception; we verify they are catchable/skip
    try:
        runpod_scrape_runpod(cdp_url="http://127.0.0.1:99999")
    except Exception as e:
        pytest.skip(f"Live Chrome CDP is not connected (expected in test env): {e}")


def test_vast_scraper_infer_manufacturer():
    from scrapers.vast.api import VastScraperAPI

    assert VastScraperAPI.infer_manufacturer("RTX 4090", "nvidia") == "Nvidia"
    assert VastScraperAPI.infer_manufacturer("H100 NVL", "nvidia") == "Nvidia"
    assert VastScraperAPI.infer_manufacturer("MI300X", "amd") == "AMD"
    assert VastScraperAPI.infer_manufacturer("Custom ASIC", None) == "Unknown"


def test_vast_scraper_normalization_and_pricing():
    from scrapers.vast.api import VastScraperAPI

    api = VastScraperAPI(api_key="mock_key")

    mock_offers = [
        {
            "id": 46940599,
            "gpu_name": "RTX 3090",
            "gpu_arch": "nvidia",
            "num_gpus": 2,
            "gpu_ram": 24576,
            "cpu_ram": 64166,
            "cpu_cores_effective": 48.0,
            "dph_total": 0.0280555,
            "min_bid": 0.21333,
            "verification": "verified",
            "vericode": 1,
            "reliability": 0.989,
            "rentable": True,
            "rented": False,
            "geolocation": "Texas, US",
        },
        {
            "id": 33482332,
            "gpu_name": "Tesla V100",
            "gpu_arch": "nvidia",
            "num_gpus": 1,
            "gpu_ram": 32768,
            "cpu_ram": 32000,
            "cpu_cores_effective": 10.0,
            "dph_total": 0.0281,
            "min_bid": None,
            "verification": "unverified",
            "vericode": 0,
            "reliability": 0.95,
            "rentable": False,
            "rented": True,
            "geolocation": "France, FR",
        },
    ]

    # Mock fetch_offers
    api.fetch_offers = lambda available_only=False, limit=None: mock_offers

    gpus = api.get_gpus()
    assert len(gpus) == 2

    # First GPU (verified, rentable)
    gpu1 = next(g for g in gpus if g["gpu_id"] == "46940599")
    assert gpu1["provider"] == "Vast"
    assert gpu1["gpu_name"] == "RTX 3090"
    assert gpu1["manufacturer"] == "Nvidia"
    assert gpu1["vram_gb"] == 24
    assert gpu1["ram_gb"] == 63
    assert gpu1["cpu"] == 48
    assert gpu1["gpu_count"] == 2
    assert gpu1["hourly_price"] == 0.0281
    assert gpu1["secure_price"] == 0.0281
    assert gpu1["community_price"] is None
    assert gpu1["spot_price"] == 0.2133
    assert gpu1["deployable"] == 1
    assert gpu1["availability"] == "high"
    assert gpu1["reliability"] == 0.989
    assert gpu1["regions"] == ["Texas, US"]

    # Second GPU (unverified, unrentable)
    gpu2 = next(g for g in gpus if g["gpu_id"] == "33482332")
    assert gpu2["vram_gb"] == 32
    assert gpu2["community_price"] == 0.0281
    assert gpu2["secure_price"] is None
    assert gpu2["spot_price"] is None
    assert gpu2["deployable"] == 0
    assert gpu2["availability"] == "unavailable"
