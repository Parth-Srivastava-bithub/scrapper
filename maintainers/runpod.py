from typing import Any, Dict, List, Optional
from rich import print

from database.mongo import get_datacenters_collection, get_db
from maintainers.base import update_live_fields, upsert_many
from scrapers.runpod.cli import sync_runpod_datacenters_cli, sync_runpod_gpus_cli
from scrapers.runpod.graphql import runpod_get_gpus


class RunpodMaintainer:
    """RunPod Maintainer with multi-tier fallback architecture:
    1. Primary: runpodctl CLI ('runpodctl gpu list')
    2. Second Fallback: RunPod GraphQL API
    3. Final Fallback: Preserved cached data in MongoDB
    """

    def __init__(self):
        self.db = get_db()
        self.datacenters_collection = get_datacenters_collection()

    def get_stored_catalog(self) -> List[Dict[str, Any]]:
        """Retrieve existing RunPod records stored in the database."""
        collection = self.db["gpu_catalog"]
        return list(collection.find({"provider": {"$regex": "^runpod$", "$options": "i"}}))

    def fetch_gpu_catalog(self) -> List[Dict[str, Any]]:
        """Fetch GPU catalog using the 3-tier fallback strategy."""
        # 1. Primary: runpodctl CLI
        try:
            print("[cyan][INFO] [RunPod] Trying Primary source: runpodctl CLI...[/cyan]")
            cli_data = sync_runpod_gpus_cli()
            if cli_data and isinstance(cli_data, list) and len(cli_data) > 0:
                print(f"[green][OK] [RunPod] Successfully fetched {len(cli_data)} GPUs via runpodctl CLI (Primary).[/green]")
                return cli_data
            else:
                print("[yellow][WARN] [RunPod] runpodctl CLI returned empty data.[/yellow]")
        except Exception as e:
            print(f"[yellow][WARN] [RunPod] Primary source (runpodctl CLI) failed: {e}[/yellow]")

        # 2. Second Fallback: RunPod GraphQL API
        try:
            print("[cyan][INFO] [RunPod] Falling back to Secondary source: RunPod GraphQL API...[/cyan]")
            graphql_data = runpod_get_gpus()
            if isinstance(graphql_data, list) and len(graphql_data) > 0:
                print(f"[green][OK] [RunPod] Successfully fetched {len(graphql_data)} GPUs via GraphQL (Secondary Fallback).[/green]")
                return graphql_data
            elif isinstance(graphql_data, dict) and "error" in graphql_data:
                print(f"[yellow][WARN] [RunPod] GraphQL returned error: {graphql_data['error']}[/yellow]")
            else:
                print("[yellow][WARN] [RunPod] GraphQL returned empty data.[/yellow]")
        except Exception as e:
            print(f"[yellow][WARN] [RunPod] Secondary source (GraphQL) failed: {e}[/yellow]")

        # 3. Final Fallback: Existing stored data in MongoDB
        try:
            stored = self.get_stored_catalog()
            if stored:
                print(f"[magenta][DB] [RunPod] Final Fallback: Retaining {len(stored)} existing GPUs stored in MongoDB.[/magenta]")
                return stored
            else:
                print("[red][ERROR] [RunPod] No existing RunPod data found in database cache.[/red]")
        except Exception as e:
            print(f"[red][ERROR] [RunPod] Failed to inspect MongoDB cache: {e}[/red]")

        return []

    def update_catalog(self):
        """Fetch RunPod catalog via tiered fallback and upsert into MongoDB."""
        print("\n========== RunPod Catalog Maintainer ==========")
        data = self.fetch_gpu_catalog()

        if data:
            upsert_many(data)
        else:
            print("[red][ERROR] [RunPod] Catalog update aborted: No data available from CLI, GraphQL, or DB.[/red]")

    def sync_datacenters(self):
        """Fetch datacenters via runpodctl and upsert into datacenters collection."""
        print("\n========== RunPod Datacenters Maintainer ==========")
        try:
            data = sync_runpod_datacenters_cli()
            for dc in data:
                self.datacenters_collection.update_one(
                    {"_id": f"runpod>{dc['id']}"},
                    {
                        "$set": {
                            "provider": "Runpod",
                            "datacenter_id": dc["id"],
                            "name": dc.get("name", dc["id"]),
                            "location": dc.get("location", ""),
                            "gpuAvailability": dc.get("gpuAvailability", []),
                        }
                    },
                    upsert=True,
                )
            print(f"[green][OK] Synced {len(data)} RunPod datacenters.[/green]")
        except Exception as e:
            print(f"[yellow][WARN] Failed to sync RunPod datacenters: {e}[/yellow]")

    def live_sync(self):
        """Fetch latest live pricing/stock using tiered fallback and update MongoDB."""
        print("\n========== RunPod Live Update ==========")
        # 1. Primary: runpodctl CLI
        try:
            cli_data = sync_runpod_gpus_cli()
            if cli_data and isinstance(cli_data, list) and len(cli_data) > 0:
                update_live_fields(cli_data)
                print(f"[green][OK] Live updated {len(cli_data)} RunPod GPUs via runpodctl CLI (Primary).[/green]")
                return
        except Exception as e:
            print(f"[yellow][WARN] Live sync CLI failed: {e}. Trying GraphQL...[/yellow]")

        # 2. Second Fallback: GraphQL
        try:
            graphql_data = runpod_get_gpus()
            if isinstance(graphql_data, list) and len(graphql_data) > 0:
                update_live_fields(graphql_data)
                print(f"[green][OK] Live updated {len(graphql_data)} RunPod GPUs via GraphQL (Secondary Fallback).[/green]")
                return
            elif isinstance(graphql_data, dict) and "error" in graphql_data:
                print(f"[yellow][WARN] GraphQL live update error: {graphql_data['error']}[/yellow]")
        except Exception as e:
            print(f"[yellow][WARN] Live sync GraphQL failed: {e}.[/yellow]")

        # 3. Final Fallback: Database stored data preserved
        stored_count = len(self.get_stored_catalog())
        print(f"[magenta][DB] Live update failed for live sources; {stored_count} stored RunPod entries preserved in DB.[/magenta]")
