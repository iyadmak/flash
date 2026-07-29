"""One-off setup: creates the `analytics` MongoDB database.

MongoDB does not persist a database with zero collections, so creating one
explicitly is what makes the database real.
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
