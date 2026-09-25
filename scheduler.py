from apscheduler.schedulers.blocking import BlockingScheduler
from rich import print

from database.mongo import create_database
from maintainers.novita import NovitaMaintainer
from maintainers.runpod import RunpodMaintainer
from maintainers.vast import VastMaintainer

scheduler = BlockingScheduler()

runpod_maintainer = RunpodMaintainer()
novita_maintainer = NovitaMaintainer()
vast_maintainer = VastMaintainer()


# =========================================================
# GPU Catalog
# =========================================================


def update_runpod_catalog():
    runpod_maintainer.update_catalog()


def update_novita_catalog():
    novita_maintainer.update_catalog()


def update_vast_catalog():
    vast_maintainer.update_catalog()


# =========================================================
# Datacenters
# =========================================================


def sync_runpod_datacenters():
    runpod_maintainer.sync_datacenters()


def sync_novita_datacenters():
    novita_maintainer.sync_datacenters()


def sync_vast_datacenters():
    vast_maintainer.sync_datacenters()


# =========================================================
# Live Updates
# =========================================================


def runpod_live_sync():
    runpod_maintainer.live_sync()


def novita_live_sync():
    novita_maintainer.live_sync()


def vast_live_sync():
    vast_maintainer.live_sync()


# =========================================================
# Initial Sync
# =========================================================


def initial_sync():
    print("\n=========== INITIAL SYNC ===========")

    try:
        update_runpod_catalog()
    except Exception as e:
        print(f"⚠️ RunPod catalog update skipped/failed: {e}")

    try:
        update_novita_catalog()
    except Exception as e:
        print(f"⚠️ Novita catalog update skipped/failed: {e}")

    try:
        update_vast_catalog()
    except Exception as e:
        print(f"⚠️ Vast catalog update skipped/failed: {e}")

    try:
        sync_runpod_datacenters()
    except Exception as e:
        print(f"⚠️ RunPod datacenters sync skipped/failed: {e}")

    try:
        sync_novita_datacenters()
    except Exception as e:
        print(f"⚠️ Novita datacenters sync skipped/failed: {e}")

    try:
        sync_vast_datacenters()
    except Exception as e:
        print(f"⚠️ Vast datacenters sync skipped/failed: {e}")

    print("\nInitial Sync Complete")


# =========================================================
# Scheduler Job Setup
# =========================================================

scheduler.add_job(
    update_runpod_catalog,
    "interval",
    hours=1,
    id="runpod_catalog",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    update_novita_catalog,
    "interval",
    hours=1,
    id="novita_catalog",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    update_vast_catalog,
    "interval",
    hours=1,
    id="vast_catalog",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    sync_runpod_datacenters,
    "interval",
    hours=4,
    id="runpod_datacenters",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    sync_novita_datacenters,
    "interval",
    hours=4,
    id="novita_datacenters",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    sync_vast_datacenters,
    "interval",
    hours=4,
    id="vast_datacenters",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    runpod_live_sync,
    "interval",
    minutes=5,
    id="runpod_live",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    novita_live_sync,
    "interval",
    minutes=5,
    id="novita_live",
    max_instances=1,
    coalesce=True,
)

scheduler.add_job(
    vast_live_sync,
    "interval",
    minutes=5,
    id="vast_live",
    max_instances=1,
    coalesce=True,
)


if __name__ == "__main__":
    print("Initializing database...")
    create_database()

    print("Running initial sync...")
    initial_sync()

    print("Scheduler started...")
    scheduler.start()
