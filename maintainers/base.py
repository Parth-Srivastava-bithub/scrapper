from datetime import datetime

from pymongo import UpdateOne
from rich import print

from database.mongo import get_gpu_catalog_collection


def make_gpu_id(provider, gpu_id):
    if ">" in str(gpu_id):
        return str(gpu_id)
    return f"{provider.lower()}>{gpu_id}"


def upsert_many(merged):
    if not merged:
        return

    collection = get_gpu_catalog_collection()
    operations = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for gpu in merged:
        full_gpu_id = make_gpu_id(gpu["provider"], gpu["gpu_id"])
        doc = {
            "provider": gpu["provider"],
            "gpu_id": full_gpu_id,
            "gpu_name": gpu["gpu_name"],
            "manufacturer": gpu.get("manufacturer"),
            "vram_gb": gpu.get("vram_gb"),
            "ram_gb": gpu.get("ram_gb"),
            "cpu": gpu.get("cpu"),
            "gpu_count": gpu.get("gpu_count"),
            "hourly_price": gpu.get("hourly_price"),
            "community_price": gpu.get("community_price"),
            "secure_price": gpu.get("secure_price"),
            "spot_price": gpu.get("spot_price"),
            "availability": gpu.get("availability"),
            "deployable": int(gpu.get("deployable", 0)),
            "reliability": gpu.get("reliability"),
            "updated_at": now_str,
        }
        operations.append(
            UpdateOne(
                {"_id": full_gpu_id},
                {"$set": doc},
                upsert=True,
            )
        )

    if operations:
        collection.bulk_write(operations)

    print(f"Upserted {len(operations)} GPUs.")


def update_live_fields(graphql_data):
    if not graphql_data:
        return

    collection = get_gpu_catalog_collection()
    operations = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for gpu in graphql_data:
        full_gpu_id = make_gpu_id(gpu["provider"], gpu["gpu_id"])
        update_fields = {
            "hourly_price": gpu.get("hourly_price"),
            "community_price": gpu.get("community_price"),
            "secure_price": gpu.get("secure_price"),
            "spot_price": gpu.get("spot_price"),
            "availability": gpu.get("availability"),
            "deployable": int(gpu.get("deployable", 0)),
            "reliability": gpu.get("reliability"),
            "updated_at": now_str,
        }
        operations.append(
            UpdateOne(
                {"_id": full_gpu_id},
                {"$set": update_fields},
            )
        )

    if operations:
        collection.bulk_write(operations)

    print(f"Updated {len(operations)} GPUs.")
