
import os

from rich import print

from database.mongo import get_datacenters_collection, get_db
from maintainers.base import update_live_fields, upsert_many
from scrapers.runpod.cli import sync_runpod_datacenters_cli
from scrapers.runpod.graphql import runpod_get_gpus
from scrapers.runpod.playwright import runpod_merge, runpod_scrape_runpod


class RunpodMaintainer:
    """RunPod Maintainer responsible for data transformation and DB synchronization."""

    def __init__(self):
        self.db = get_db()
        self.datacenters_collection = get_datacenters_collection()

    def update_catalog(self, cdp_url: str | None = None):
        """Scrape via Playwright and GraphQL, merge, and upsert into MongoDB."""
        print("\n========== RunPod Catalog Maintainer ==========")
        cdp_url = cdp_url or os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222")
        playwright_data = runpod_scrape_runpod(cdp_url=cdp_url)
        graphql_data = runpod_get_gpus()

        if isinstance(graphql_data, dict) and "error" in graphql_data:
            print(f"❌ Error fetching RunPod GraphQL data: {graphql_data['error']}")
            return

        if playwright_data and isinstance(graphql_data, list):
            merged = runpod_merge(playwright_data, graphql_data)
            upsert_many(merged)
        elif isinstance(graphql_data, list):
            print("⚠️ Playwright data empty; upserting RunPod GraphQL catalog directly.")
            upsert_many(graphql_data)

    def sync_datacenters(self):
        """Fetch datacenters via runpodctl and upsert into datacenters collection."""
        print("\n========== RunPod Datacenters Maintainer ==========")
        data = sync_runpod_datacenters_cli()

        for dc in data:
            self.datacenters_collection.update_one(
                {"_id": f"runpod>{dc['id']}"},
                {
                    "$set": {
                        "provider": "Runpod",
                        "datacenter_id": dc["id"],
                        "name": dc["name"],
                        "location": dc["location"],
                        "gpuAvailability": dc.get("gpuAvailability", []),
                    }
                },
                upsert=True,
            )
        print(f"Synced {len(data)} RunPod datacenters.")

    def live_sync(self):
        """Fetch latest live pricing/stock from GraphQL and update MongoDB."""
        print("\nRunPod Live Update")
        graphql_data = runpod_get_gpus()
        if isinstance(graphql_data, list):
            update_live_fields(graphql_data)
        else:
            print(f"❌ Error in live sync: {graphql_data}")
