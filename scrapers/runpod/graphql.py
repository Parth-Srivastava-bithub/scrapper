import os

import requests
from dotenv import load_dotenv

load_dotenv()

QUERY = """
query {
  gpuTypes {
    id
    displayName
    manufacturer
    memoryInGb

    communityPrice
    securePrice

    maxGpuCount

    lowestPrice(
      input: {
        gpuCount: 1
        secureCloud: false
      }
    ) {
      stockStatus
      uninterruptablePrice
    }
  }
}
"""


def runpod_get_gpus():
    url = "https://api.runpod.io/graphql"

    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, json={"query": QUERY})
        data = response.json()
        gpu_types = data["data"]["gpuTypes"]

        result = []
        for gpu in gpu_types:
            lowest = gpu.get("lowestPrice")

            result.append(
                {
                    "provider": "RunPod",
                    "gpu_id": gpu.get("id"),
                    "gpu_name": gpu["displayName"],
                    "vram_gb": gpu["memoryInGb"],
                    "manufacturer": gpu["manufacturer"],
                    "community_price": gpu["communityPrice"],
                    "hourly_price": gpu["securePrice"],
                    "secure_price": (
                        lowest.get("uninterruptablePrice")
                        if lowest and lowest.get("uninterruptablePrice") is not None
                        else gpu.get("communityPrice")
                    ),
                    "spot_price": None,
                    "availability": (
                        (lowest.get("stockStatus") or "unavailable").lower()
                        if lowest
                        else "unavailable"
                    ),
                    "deployable": (
                        lowest is not None
                        and lowest.get("uninterruptablePrice") is not None
                    ),
                    "regions": None,
                    "gpu_count": gpu["maxGpuCount"],
                    "reliability": None,
                    "cpu": None,
                    "ram_gb": None,
                }
            )

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

        result.sort(key=lambda x: availability_rank(x["availability"]), reverse=True)
        return result

    except Exception as e:
        return {"error": str(e)}
