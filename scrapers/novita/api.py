import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()


class NovitaScraperAPI:
    def __init__(self):
        self.api_key = os.getenv("NOVITA_API_KEY")
        self.url = "https://api.novita.ai"
        self.region_endpoint = "https://api.novita.ai/gpus/v2/regions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def extract_vram(name):
        match = re.search(r"(\d+)GB", name)
        return int(match.group(1)) if match else None

    @staticmethod
    def availability_rank(status):
        s = str(status).lower()
        if s == "high":
            return 4
        elif s == "normal":
            return 3
        elif s == "low":
            return 2
        else:
            return 1

    def get_gpus(self):
        response = requests.get(
            f"{self.url}/gpu-instance/openapi/v1/products", headers=self.headers
        )
        data = response.json()
        result = []

        for gpu in data.get("data", []):
            name = gpu.get("name", "").upper()

            if "NVIDIA" in name or "RTX" in name or "H100" in name or "A100" in name:
                manufacturer = "Nvidia"
            elif "AMD" in name or "MI300" in name:
                manufacturer = "AMD"
            else:
                manufacturer = "Unknown"

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
                        if gpu.get("spotPrice") and gpu["spotPrice"] != "0"
                        else None
                    ),
                    "availability": gpu.get("inventoryState", "unavailable").lower(),
                    "deployable": gpu.get("availableDeploy", False),
                    "regions": gpu.get("regions", []),
                    "gpu_count": 1,
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

    def get_regions(self):
        response = requests.get(self.region_endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", [])
