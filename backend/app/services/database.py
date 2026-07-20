from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local dev
    MongoClient = None
    Database = Any
    Collection = Any


MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "bug_bounty_hunter")


@lru_cache(maxsize=1)
def get_database() -> Database | None:
    if MongoClient is None:
        return None
    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=1500)
        client.admin.command("ping")
        return client[MONGODB_DB_NAME]
    except Exception:
        return None


def is_mongo_available() -> bool:
    return get_database() is not None


def get_collection(name: str) -> Collection | None:
    database = get_database()
    if database is None:
        return None
    return database[name]


def reset_database_cache() -> None:
    get_database.cache_clear()
