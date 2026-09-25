import os

import certifi
# pyrefly: ignore [missing-import]
import pymongo
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from pymongo import MongoClient
# pyrefly: ignore [missing-import]
from pymongo.server_api import ServerApi

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "gpu_aggregator")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a shared MongoClient instance."""
    global _client
    if _client is None:
        kwargs = {}
        if (
            MONGODB_URI.startswith("mongodb+srv://")
            or "ssl=true" in MONGODB_URI.lower()
            or "tls=true" in MONGODB_URI.lower()
        ):
            try:
                kwargs["tlsCAFile"] = certifi.where()
                kwargs["server_api"] = ServerApi("1")
            except Exception:
                pass
        _client = MongoClient(MONGODB_URI, **kwargs)
    return _client


def get_db():
    """Return the application MongoDB database."""
    client = get_client()
    return client[MONGODB_DB_NAME]


def get_gpu_catalog_collection():
    """Return the gpu_catalog collection."""
    return get_db()["gpu_catalog"]


def get_datacenters_collection():
    """Return the datacenters collection."""
    return get_db()["datacenters"]


def create_database():
    """Ensure database collections and necessary indexes exist."""
    db = get_db()
    gpu_catalog = db["gpu_catalog"]

    # 1. Unique index on gpu_id
    gpu_catalog.create_index(
        [("gpu_id", pymongo.ASCENDING)],
        unique=True,
        name="idx_gpu_id_unique",
    )

    # 2. Index on provider and hourly_price
    gpu_catalog.create_index(
        [("provider", pymongo.ASCENDING), ("hourly_price", pymongo.ASCENDING)],
        name="idx_provider_hourly_price",
    )

    # 3. Index on provider, deployable, and hourly_price
    gpu_catalog.create_index(
        [
            ("provider", pymongo.ASCENDING),
            ("deployable", pymongo.ASCENDING),
            ("hourly_price", pymongo.ASCENDING),
        ],
        name="idx_provider_deployable_price",
    )

    # 4. Compound index on provider and gpu_name for specific GPU lookups
    gpu_catalog.create_index(
        [("provider", pymongo.ASCENDING), ("gpu_name", pymongo.ASCENDING)],
        name="idx_provider_gpu_name",
    )

    print("MongoDB collections and indexes initialized successfully.")
