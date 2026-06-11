"""Item Tests"""

from fastapi.testclient import TestClient
from flash.api.deps import get_item_service
from flash.main import app
from flash.schemas.item import Item


class FakeItemService:
    """Fake item service"""

    def get_items(self) -> list[Item]:
        """Get fake items"""
        return [Item(id=1, name="test item", price=100.0)]


def test_get_item(client: TestClient) -> None:
    """Test Get Item"""
    app.dependency_overrides[get_item_service] = FakeItemService
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "test item"
    app.dependency_overrides.clear()
