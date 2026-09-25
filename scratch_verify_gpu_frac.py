import os
import requests
from dotenv import load_dotenv

load_dotenv()

headers = {
    "Authorization": "Bearer " + os.getenv("VASTAI_API_KEY"),
    "Content-Type": "application/json"
}

resp = requests.post(
    "https://console.vast.ai/api/v0/bundles/",
    headers=headers,
    json={"limit": 1000, "type": "on-demand", "allocated_storage": 5.0, "rentable": {"in": [True, False]}}
)
offers = resp.json().get("offers", [])

print(f"Total offers fetched: {len(offers)}")
print(f"Unique num_gpus: {sorted(set(o.get('num_gpus') for o in offers))}")

# Check 1: len(gpu_ids) vs num_gpus
mismatched_ids = [o for o in offers if len(o.get('gpu_ids') or []) != o.get('num_gpus')]
print(f"Offers where len(gpu_ids) != num_gpus: {len(mismatched_ids)}")
if mismatched_ids:
    for o in mismatched_ids[:3]:
        print(f"  id={o['id']}, num_gpus={o.get('num_gpus')}, gpu_ids={o.get('gpu_ids')}, gpu_frac={o.get('gpu_frac')}")

# Check 2: gpu_total_ram vs gpu_ram * num_gpus
mismatched_vram = [o for o in offers if o.get('gpu_total_ram') != o.get('gpu_ram') * o.get('num_gpus')]
print(f"Offers where gpu_total_ram != gpu_ram * num_gpus: {len(mismatched_vram)}")

# Check 3: gpu_frac relationship with machine total GPUs
print("\nSample offers showing exact relationships:")
for o in offers[:10]:
    total_machine_gpus = round(o['num_gpus'] / o['gpu_frac']) if o.get('gpu_frac') else 'N/A'
    print(f"Offer ID: {o['id']}")
    print(f"  GPU Name: {o['gpu_name']}")
    print(f"  num_gpus (in this offer): {o.get('num_gpus')}")
    print(f"  len(gpu_ids): {len(o.get('gpu_ids') or [])} -> gpu_ids={o.get('gpu_ids')}")
    print(f"  gpu_frac (offer share of whole machine): {o.get('gpu_frac')}")
    print(f"  Calculated host total GPUs (num_gpus / gpu_frac): {total_machine_gpus}")
    print(f"  gpu_ram (per GPU MB): {o.get('gpu_ram')} (={round(o.get('gpu_ram', 0)/1024, 1)} GB)")
    print(f"  gpu_total_ram (offer total MB): {o.get('gpu_total_ram')} (={round(o.get('gpu_total_ram', 0)/1024, 1)} GB)")
    print(f"  cpu_cores (host total): {o.get('cpu_cores')}")
    print(f"  cpu_cores_effective (offer allocated): {o.get('cpu_cores_effective')} (={o.get('cpu_cores') * o.get('gpu_frac')})")
    print("-" * 50)
