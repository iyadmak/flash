"""One-off setup script: creates the `analytics` MongoDB database.

MongoDB doesn't persist an empty database -- one with zero collections
never shows up in list_database_names() and vanishes once every client
disconnects. Explicitly creating a collection (rather than just connecting,
or inserting a throwaway document as a workaround) is the correct way to
make the database real before any reporting feature writes to it.
"""

import asyncio
from flash.core.adapters.mongodb import ANALYTICS_DB_NAME, get_mongo_client


async def main() -> None:
    client = get_mongo_client()
    db = client.get_database(ANALYTICS_DB_NAME)

    existing = await db.list_collection_names()
    if "reports" not in existing:
        await db.create_collection("reports")
        print(f"Created collection 'reports' in database {ANALYTICS_DB_NAME!r}.")
    else:
        print(f"Collection 'reports' already exists in {ANALYTICS_DB_NAME!r}.")

    names = await client.list_database_names()
    print(f"Databases now on the server: {names}")
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
