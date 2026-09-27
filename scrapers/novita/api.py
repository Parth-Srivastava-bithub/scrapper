import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class NovitaScraperAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("NOVITA_API_KEY") or "").strip('"').strip("'")
        self.url = "https://api.novita.ai"
        self.products_endpoint = f"{self.url}/gpu-instance/openapi/v1/products"
        self.region_endpoint = f"{self.url}/gpus/v2/regions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def extract_vram(name: str) -> Optional[int]:
        match = re.search(r"(\d+)GB", name)
        return int(match.group(1)) if match else None

    @staticmethod
    def availability_rank(status: Any) -> int:
        s = str(status).lower()
        if s in ("high", "yes", "available"):
            return 4
        elif s == "normal":
            return 3
        elif s == "low":
            return 2
        else:
            return 1

    def get_products_raw(self, gpu_num: Optional[int] = 1) -> List[Dict[str, Any]]:
        """Fetch raw products directly matching `novita gpu products --gpu-num <n>`."""
        params = {}
        if gpu_num is not None:
            params["gpuNum"] = gpu_num
        response = requests.get(
            self.products_endpoint,
            headers=self.headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def get_gpus(self, gpu_num: Optional[int] = 1) -> List[Dict[str, Any]]:
        """Fetch parsed GPU list with pricing and availability."""
        products = self.get_products_raw(gpu_num=gpu_num)
        result = []

        for gpu in products:
            name = gpu.get("name", "").upper()

            if "NVIDIA" in name or "RTX" in name or "H100" in name or "A100" in name:
                manufacturer = "Nvidia"
            elif "AMD" in name or "MI300" in name:
                manufacturer = "AMD"
            else:
                manufacturer = "Unknown"

            available_deploy = bool(gpu.get("availableDeploy", False))
            inventory_state = str(gpu.get("inventoryState", "none")).lower()
            if available_deploy:
                availability = (
                    inventory_state
                    if inventory_state not in ("none", "unavailable", "")
                    else "available"
                )
            else:
                availability = "unavailable"

            result.append(
                {
                    "provider": "Novita",
                    "gpu_id": gpu.get("id"),
                    "gpu_name": gpu.get("name"),
                    "vram_gb": self.extract_vram(gpu.get("name", "")),
                    "hourly_price": (
                        int(gpu["price"]) / 100000 if gpu.get("price") else None
                    ),
                    "spot_price": (
                        int(gpu["spotPrice"]) / 100000
                        if gpu.get("spotPrice") and str(gpu["spotPrice"]) != "0"
                        else None
                    ),
                    "availability": availability,
                    "available": "Yes" if available_deploy else "No",
                    "deployable": 1 if available_deploy else 0,
                    "regions": gpu.get("regions", []),
                    "gpu_count": gpu_num if gpu_num is not None else 1,
                    "reliability": None,
                    "cpu": gpu.get("cpuPerGpu"),
                    "ram_gb": gpu.get("memoryPerGpu"),
                    "manufacturer": manufacturer,
                    "community_price": None,
                    "secure_price": None,
                }
            )
        result.sort(
            key=lambda x: self.availability_rank(x["availability"]), reverse=True
        )
        return result

    def get_gpu_availability(self, gpu_num: Optional[int] = 1) -> List[Dict[str, Any]]:
        """Get product availability matching the `novita gpu products` output."""
        products = self.get_products_raw(gpu_num=gpu_num)
        table = []
        for p in products:
            table.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "cpu_per_gpu": p.get("cpuPerGpu"),
                    "mem_per_gpu": p.get("memoryPerGpu"),
                    "price": p.get("price"),
                    "available": "Yes" if p.get("availableDeploy") else "No",
                    "deployable": bool(p.get("availableDeploy", False)),
                    "regions": p.get("regions", []),
                }
            )
        return table

    def get_datacenter_gpu_availability(
        self, gpu_num: Optional[int] = 1
    ) -> List[Dict[str, Any]]:
        """Map GPU availability per datacenter / cluster from the products endpoint."""
        products = self.get_products_raw(gpu_num=gpu_num)
        clusters: Dict[str, Dict[str, Any]] = {}

        for p in products:
            name = p.get("name")
            is_avail = bool(p.get("availableDeploy", False))
            for reg in p.get("regions", []):
                if reg not in clusters:
                    clusters[reg] = {
                        "cluster": reg,
                        "available": [],
                        "unavailable": [],
                    }
                if is_avail:
                    if name not in clusters[reg]["available"]:
                        clusters[reg]["available"].append(name)
                else:
                    if name not in clusters[reg]["unavailable"]:
                        clusters[reg]["unavailable"].append(name)

        return list(clusters.values())

    def get_regions(self):
        response = requests.get(self.region_endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", [])
