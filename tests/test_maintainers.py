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
