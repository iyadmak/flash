"""Item Service"""

import structlog

from flash.schemas.item import Item

logger = structlog.get_logger()


def get_items() -> list[Item]:
    """Get all items"""
    logger.info("Getting items")
    logger.debug(
        "Getting items",
        items=[
            {"id": 1, "name": "Item 1", "price": 100.0},
            {"id": 2, "name": "Item 2", "price": 200.0},
        ],
    )
    return [
        Item(id=1, name="Item 1", price=100.0),
        Item(id=2, name="Item 2", price=200.0),
    ]
