import json
import os
import shutil
import subprocess
from typing import Any, Dict, List


def get_runpodctl_path() -> str:
    """Find the runpodctl binary in PATH or standard installation locations."""
    # Check PATH first
    found = shutil.which("runpodctl") or shutil.which("runpodctl.exe")
    if found and os.path.exists(found):
        return found

    # Check common fallback locations on Windows and Linux
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\runpodctl\runpodctl.exe"),
        os.path.expanduser(r"~/.local/bin/runpodctl.exe"),
        os.path.expanduser(r"~/.local/bin/runpodctl"),
        r"C:\Users\user\.local\bin\runpodctl.exe",
        r"C:\Users\user\AppData\Local\runpodctl\runpodctl.exe",
        r"C:\Users\user\runpodctl.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError("runpodctl executable not found in PATH or standard directories.")


def sync_runpod_gpus_cli() -> List[Dict[str, Any]]:
    """Execute runpodctl to list GPUs and return standardized catalog dictionaries."""
    runpodctl_path = get_runpodctl_path()

    result = subprocess.run(
        [
            runpodctl_path,
            "gpu",
            "list",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    if not isinstance(data, list):
        raise ValueError(f"Unexpected response format from runpodctl gpu list: {type(data)}")

    standardized = []
    for item in data:
        gpu_id = item.get("gpuId")
        if not gpu_id:
            continue

        display_name = item.get("displayName") or gpu_id
        is_available = bool(item.get("available", False))
        stock_status = str(item.get("stockStatus") or ("low" if is_available else "unavailable")).lower()

        # Extract available datacenter IDs
        available_dcs = [
            dc.get("dataCenterId")
            for dc in item.get("dataCenterAvailability", [])
            if dc.get("dataCenterId") and str(dc.get("stockStatus", "")).lower() not in ("none", "unavailable", "")
        ]

        sec_price = item.get("securePricePerHr")
        comm_price = item.get("communityPricePerHr")
        hourly_price = sec_price if sec_price is not None else comm_price

        # Infer manufacturer
        name_upper = (display_name + " " + gpu_id).upper()
        if "AMD" in name_upper or "MI3" in name_upper or "MI2" in name_upper:
            manufacturer = "AMD"
        elif "INTEL" in name_upper or "GAUDI" in name_upper:
            manufacturer = "Intel"
        else:
            manufacturer = "Nvidia"

        standardized.append(
            {
                "provider": "RunPod",
                "gpu_id": gpu_id,
                "gpu_name": display_name,
                "vram_gb": item.get("memoryInGb"),
                "manufacturer": manufacturer,
                "community_price": comm_price,
                "hourly_price": hourly_price,
                "secure_price": sec_price,
                "spot_price": None,
                "availability": stock_status if is_available else "unavailable",
                "deployable": 1 if is_available else 0,
                "regions": available_dcs if available_dcs else None,
                "gpu_count": 8,
                "reliability": None,
                "cpu": None,
                "ram_gb": None,
            }
        )

    return standardized


def sync_runpod_datacenters_cli() -> List[Dict[str, Any]]:
    """Execute runpodctl to list datacenters in JSON format."""
    runpodctl_path = get_runpodctl_path()

    result = subprocess.run(
        [
            runpodctl_path,
            "datacenter",
            "list",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)
