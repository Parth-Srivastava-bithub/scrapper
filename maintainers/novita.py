import re

from rich import print

from database.mongo import get_datacenters_collection, get_db
from maintainers.base import update_live_fields, upsert_many
from scrapers.novita.api import NovitaScraperAPI


class NovitaMaintainer:
    """Novita Maintainer responsible for data transformation and DB synchronization."""

    def __init__(self):
        self.api = NovitaScraperAPI()
        self.db = get_db()
        self.datacenters_collection = get_datacenters_collection()

    def update_catalog(self):
        """Fetch Novita product catalog and upsert into MongoDB."""
        print("\n========== Novita Catalog Maintainer ==========")
        gpus = self.api.get_gpus()
        upsert_many(gpus)

    def sync_datacenters(self):
        """Fetch Novita regions/datacenters and upsert into MongoDB."""
        print("\n========== Novita Datacenters Maintainer ==========")
        regions = self.api.get_regions()

        for region in regions:
            gpu_availability = [
                {"gpu_name": gpu, "available": True} for gpu in region.get("gpus", [])
            ]

            match = re.match(r"(.+?)\s+\((.+)\)", region.get("name", ""))
            location = match.group(2) if match else ""

            self.datacenters_collection.update_one(
                {"_id": f"novita>{region['id']}"},
                {
                    "$set": {
                        "provider": "Novita",
                        "datacenter_id": region["id"],
                        "name": region.get("name"),
                        "location": location,
                        "gpuAvailability": gpu_availability,
                        "network_volume": region.get("feature", {}).get(
                            "network_volume", False
                        ),
                        "instance_vpc_network": region.get("feature", {}).get(
                            "instance_vpc_network", False
                        ),
                    }
                },
                upsert=True,
            )
        print(f"Synced {len(regions)} Novita datacenters.")

    def live_sync(self):
        """Fetch live catalog and update availability/prices."""
        print("\nNovita Live Update")
        gpus = self.api.get_gpus()
        update_live_fields(gpus)
