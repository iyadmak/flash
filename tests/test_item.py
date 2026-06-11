"""Item Tests"""

from fastapi.testclient import TestClient


def test_get_item(client: TestClient) -> None:
    """Test Get Item"""
    response = client.get("/api/v1/items")
    assert response.status_code == 200
