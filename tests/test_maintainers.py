"""Tests for scraper-worker maintainers and upsert operations."""

import pytest

from database.mongo import create_database, get_gpu_catalog_collection
from maintainers.base import make_gpu_id, update_live_fields, upsert_many
from maintainers.novita import NovitaMaintainer
from maintainers.runpod import RunpodMaintainer
from maintainers.vast import VastMaintainer


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    create_database()


def test_make_gpu_id():
    assert make_gpu_id("Runpod", "RTX4090") == "runpod>RTX4090"
    assert make_gpu_id("runpod", "runpod>RTX4090") == "runpod>RTX4090"
    assert make_gpu_id("Novita", "4090.16c62g.os") == "novita>4090.16c62g.os"
    assert make_gpu_id("Vast", "46940599") == "vast>46940599"


def test_maintainer_upsert_and_live_updates():
    collection = get_gpu_catalog_collection()
    test_id = "test_vm>test_gpu_maintainer"

    test_data = [
        {
            "provider": "test_vm",
            "gpu_id": "test_gpu_maintainer",
            "gpu_name": "VM Test GPU",
            "manufacturer": "VMCorp",
            "vram_gb": 32,
            "ram_gb": 64,
            "cpu": 8,
            "gpu_count": 1,
            "hourly_price": 2.50,
            "community_price": 2.00,
            "secure_price": 2.50,
            "spot_price": None,
            "availability": "high",
            "deployable": 1,
            "reliability": 0.98,
        }
    ]

    try:
        upsert_many(test_data)
        doc = collection.find_one({"_id": test_id})
        assert doc is not None
        assert doc["gpu_name"] == "VM Test GPU"
        assert doc["hourly_price"] == 2.50

        # Test live update
        update_live_fields(
            [
                {
                    "provider": "test_vm",
                    "gpu_id": "test_gpu_maintainer",
                    "hourly_price": 1.99,
                    "community_price": 1.50,
                    "secure_price": 1.99,
                    "spot_price": 0.99,
                    "availability": "low",
                    "deployable": 0,
                    "reliability": 0.95,
                }
            ]
        )
        updated = collection.find_one({"_id": test_id})
        assert updated["hourly_price"] == 1.99
        assert updated["spot_price"] == 0.99
        assert updated["reliability"] == 0.95
        assert updated["availability"] == "low"
        assert updated["deployable"] == 0
    finally:
        collection.delete_one({"_id": test_id})


def test_maintainer_classes_instantiation():
    runpod_m = RunpodMaintainer()
    novita_m = NovitaMaintainer()
    vast_m = VastMaintainer()
    assert runpod_m is not None
    assert novita_m is not None
    assert vast_m is not None


def test_runpod_maintainer_fallback_hierarchy(monkeypatch):
    runpod_m = RunpodMaintainer()

    # Tier 1: CLI succeeds
    fake_cli = [
        {
            "provider": "RunPod",
            "gpu_id": "MOCK_GPU_CLI",
            "gpu_name": "Mock CLI GPU",
            "vram_gb": 80,
            "hourly_price": 1.50,
            "availability": "low",
            "deployable": 1,
        }
    ]
    monkeypatch.setattr("maintainers.runpod.sync_runpod_gpus_cli", lambda: fake_cli)
    res_cli = runpod_m.fetch_gpu_catalog()
    assert len(res_cli) == 1
    assert res_cli[0]["gpu_id"] == "MOCK_GPU_CLI"

    # Tier 2: CLI fails -> GraphQL succeeds
    fake_gql = [
        {
            "provider": "RunPod",
            "gpu_id": "MOCK_GPU_GQL",
            "gpu_name": "Mock GraphQL GPU",
            "vram_gb": 80,
            "hourly_price": 1.50,
            "availability": "low",
            "deployable": 1,
        }
    ]

    def raise_cli():
        raise RuntimeError("CLI failed")

    monkeypatch.setattr("maintainers.runpod.sync_runpod_gpus_cli", raise_cli)
    monkeypatch.setattr("maintainers.runpod.runpod_get_gpus", lambda: fake_gql)
    res_gql = runpod_m.fetch_gpu_catalog()
    assert len(res_gql) == 1
    assert res_gql[0]["gpu_id"] == "MOCK_GPU_GQL"

    # Tier 3: CLI and GraphQL fail -> DB cache used
    def raise_gql():
        raise RuntimeError("GraphQL failed")

    monkeypatch.setattr("maintainers.runpod.runpod_get_gpus", raise_gql)
    monkeypatch.setattr(runpod_m, "get_stored_catalog", lambda: [{"gpu_id": "STORED_DB_GPU"}])
    res_db = runpod_m.fetch_gpu_catalog()
    assert len(res_db) == 1
    assert res_db[0]["gpu_id"] == "STORED_DB_GPU"

