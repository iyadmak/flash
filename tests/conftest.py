"""Test Configuration"""

import pytest
from fastapi.testclient import TestClient

from flash.main import app


@pytest.fixture
def client() -> TestClient:
    """Test Client"""
    return TestClient(app)
