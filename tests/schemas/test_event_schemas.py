"""Guards the committed JSON Schema for each event contract against
accidental drift -- any change to OrderCreatedEvent/OrderCreatedData must be
accompanied by a deliberate regeneration of the matching snapshot file."""

import json
from pathlib import Path

from flash.schemas.order_schema import OrderCreatedEvent

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


def test_order_created_schema_matches_committed_snapshot() -> None:
    current = OrderCreatedEvent.model_json_schema()
    committed = json.loads((SNAPSHOTS_DIR / "order_created.v1.schema.json").read_text())
    assert current == committed
