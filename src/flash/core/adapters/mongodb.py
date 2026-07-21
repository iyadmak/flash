from typing import Any
from functools import lru_cache
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from flash.core.config import get_settings

ANALYTICS_DB_NAME = "analytics"


@lru_cache
def get_mongo_client() -> AsyncMongoClient[dict[str, Any]]:
    return AsyncMongoClient(get_settings().mongodb_url)


def get_analytics_db() -> AsyncDatabase[dict[str, Any]]:
    return get_mongo_client().get_database(ANALYTICS_DB_NAME)
