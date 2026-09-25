import os
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class VastScraperAPI:
    """Vast.ai Scraper API client for querying and normalizing GPU offers."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("VASTAI_API_KEY", "")
        self.base_url = (base_url or "https://console.vast.ai/api/v0").rstrip("/")
        self.bundles_url = f"{self.base_url}/bundles/"

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "gpu-aggregator-scraper/1.0",
        }
        if self.api_key:
            auth_header = self.api_key if self.api_key.startswith("Bearer ") else f"Bearer {self.api_key}"
            headers["Authorization"] = auth_header
        return headers

    @staticmethod
    def infer_manufacturer(gpu_name: Optional[str], gpu_arch: Optional[str]) -> str:
        arch_str = (gpu_arch or "").lower()
        name_str = (gpu_name or "").upper()

        if "nvidia" in arch_str or any(
            x in name_str
            for x in [
                "RTX",
                "GTX",
                "H100",
                "H200",
                "B200",
                "B300",
                "A100",
                "A40",
                "A6000",
                "A5000",
                "A4500",
                "A4000",
                "L40",
                "L40S",
                "L4",
                "V100",
                "TITAN",
                "TESLA",
                "NVIDIA",
                "ADA",
                "GEFORCE",
            ]
        ):
            return "Nvidia"
        elif "amd" in arch_str or "mi300" in name_str or "radeon" in name_str:
            return "AMD"
        elif "intel" in arch_str or "gaudi" in name_str:
            return "Intel"
        return "Unknown"

    @staticmethod
    def availability_rank(status: str) -> int:
        s = str(status).lower()
        if s == "high":
            return 4
        elif s == "normal":
            return 3
        elif s == "low":
            return 2
        else:
            return 1

    def fetch_offers(self, available_only: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch raw offer bundles from Vast.ai REST API."""
        query_payload: Dict[str, Any] = {
            "order": [["score", "desc"]],
            "type": "on-demand",
            "allocated_storage": 5.0,
        }

        if available_only:
            query_payload["rentable"] = {"eq": True}
            query_payload["rented"] = {"eq": False}
        else:
            query_payload["rentable"] = {"in": [True, False]}

        if limit is not None:
            query_payload["limit"] = int(limit)

        try:
            response = requests.post(
                self.bundles_url,
                headers=self.headers,
                json=query_payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("offers", [])
        except Exception as e:
            # Fallback to GET endpoint if POST fails
            try:
                response = requests.get(
                    self.bundles_url,
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                offers = data.get("offers", [])
                if available_only:
                    offers = [o for o in offers if o.get("rentable") is True and not o.get("rented")]
                return offers
            except Exception:
                raise e

    def get_gpus(self, available_only: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch and normalize Vast.ai GPU catalog offers."""
        raw_offers = self.fetch_offers(available_only=available_only, limit=limit)
        results = []

        for gpu in raw_offers:
            offer_id = str(gpu.get("id"))
            gpu_name = gpu.get("gpu_name") or "Unknown GPU"
            gpu_arch = gpu.get("gpu_arch")
            manufacturer = self.infer_manufacturer(gpu_name, gpu_arch)

            # RAM & VRAM calculations (Vast reports MB)
            vram_mb = gpu.get("gpu_ram") or 0
            vram_gb = int(round(vram_mb / 1024)) if vram_mb else None

            cpu_ram_mb = gpu.get("cpu_ram") or 0
            ram_gb = int(round(cpu_ram_mb / 1024)) if cpu_ram_mb else None

            # CPU cores
            cpu_cores = gpu.get("cpu_cores_effective") or gpu.get("cpu_cores")
            cpu = int(round(cpu_cores)) if cpu_cores else None

            gpu_count = int(gpu.get("num_gpus") or 1)

            # Pricing mappings
            dph_total = gpu.get("dph_total")
            hourly_price = float(round(dph_total, 4)) if dph_total is not None else None

            is_verified = (
                gpu.get("verification") == "verified"
                or gpu.get("vericode") == 1
            )

            community_price = (
                hourly_price if (not is_verified and hourly_price is not None) else None
            )
            secure_price = (
                hourly_price if (is_verified and hourly_price is not None) else None
            )

            min_bid = gpu.get("min_bid")
            spot_price = float(round(min_bid, 4)) if (min_bid and min_bid > 0) else None

            # Availability & Deployability
            is_rentable = bool(gpu.get("rentable") is True and not gpu.get("rented"))
            reliability = float(gpu["reliability"]) if gpu.get("reliability") is not None else None

            if is_rentable:
                availability = "high" if (reliability is not None and reliability >= 0.98) else "normal"
            else:
                availability = "unavailable"

            deployable = 1 if is_rentable else 0

            # Geolocation / Region
            geo = gpu.get("geolocation")
            regions = [geo] if geo else []

            results.append(
                {
                    "provider": "Vast",
                    "gpu_id": offer_id,
                    "gpu_name": gpu_name,
                    "manufacturer": manufacturer,
                    "vram_gb": vram_gb,
                    "ram_gb": ram_gb,
                    "cpu": cpu,
                    "gpu_count": gpu_count,
                    "hourly_price": hourly_price,
                    "community_price": community_price,
                    "secure_price": secure_price,
                    "spot_price": spot_price,
                    "availability": availability,
                    "deployable": deployable,
                    "reliability": reliability,
                    "regions": regions,
                }
            )

        results.sort(
            key=lambda x: self.availability_rank(x["availability"]),
            reverse=True,
        )
        return results

    def get_datacenters(self) -> List[Dict[str, Any]]:
        """Extract regional locations and GPU availability from live Vast offers."""
        offers = self.fetch_offers(available_only=False)
        regions_map: Dict[str, Dict[str, Any]] = {}

        for gpu in offers:
            geo = gpu.get("geolocation")
            if not geo:
                continue

            dc_id = geo.lower().replace(" ", "-").replace(",", "")
            if dc_id not in regions_map:
                regions_map[dc_id] = {
                    "id": dc_id,
                    "name": f"Vast ({geo})",
                    "location": geo,
                    "gpus": {},
                }

            gpu_name = gpu.get("gpu_name")
            if gpu_name:
                is_avail = bool(gpu.get("rentable") and not gpu.get("rented"))
                if gpu_name not in regions_map[dc_id]["gpus"] or is_avail:
                    regions_map[dc_id]["gpus"][gpu_name] = is_avail

        datacenters = []
        for dc in regions_map.values():
            gpu_avail = [
                {"gpu_name": g, "available": avail}
                for g, avail in sorted(dc["gpus"].items())
            ]
            datacenters.append(
                {
                    "id": dc["id"],
                    "name": dc["name"],
                    "location": dc["location"],
                    "gpuAvailability": gpu_avail,
                }
            )

        return datacenters
