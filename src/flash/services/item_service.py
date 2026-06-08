"""Item Service"""

from flash.schemas.item import Item


def get_items() -> list[Item]:
    """Get all items"""
    return [
        Item(id=1, name="Item 1", price=100.0),
        Item(id=2, name="Item 2", price=200.0),
    ]
