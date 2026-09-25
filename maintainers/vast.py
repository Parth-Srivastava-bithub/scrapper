from rich import print

from database.mongo import get_datacenters_collection, get_db
from maintainers.base import update_live_fields, upsert_many
from scrapers.vast.api import VastScraperAPI


class VastMaintainer:
    """Vast.ai Maintainer responsible for data transformation and DB synchronization."""

    def __init__(self):
        self.api = VastScraperAPI()
        self.db = get_db()
        self.datacenters_collection = get_datacenters_collection()

    def update_catalog(self, available_only: bool = False):
        """Fetch Vast offer catalog and upsert into MongoDB."""
        print("\n========== Vast Catalog Maintainer ==========")
        gpus = self.api.get_gpus(available_only=available_only)
        upsert_many(gpus)

    def sync_datacenters(self):
        """Extract regional locations and upsert into datacenters collection."""
        print("\n========== Vast Datacenters Maintainer ==========")
        datacenters = self.api.get_datacenters()

        for dc in datacenters:
            self.datacenters_collection.update_one(
                {"_id": f"vast>{dc['id']}"},
                {
                    "$set": {
                        "provider": "Vast",
                        "datacenter_id": dc["id"],
                        "name": dc.get("name"),
                        "location": dc.get("location"),
                        "gpuAvailability": dc.get("gpuAvailability", []),
                    }
                },
                upsert=True,
            )
        print(f"Synced {len(datacenters)} Vast datacenters.")

    def live_sync(self):
        """Fetch live catalog and update availability/prices in MongoDB."""
        print("\nVast Live Update")
        gpus = self.api.get_gpus(available_only=False)
        update_live_fields(gpus)
