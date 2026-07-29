"""Unit tests for RestaurantService — no DB, no HTTP, just the service
against a fake repo.

Restaurants are public-read / owner-write, the inverse of orders: `list` and
`get` take no actor at all, and only the write methods enforce ownership.
"""

import pytest

from flash.core.exceptions import Forbidden, RestaurantNotFound
from flash.models.restaurant_model import RestaurantModel
from flash.schemas.restaurant_schema import RestaurantCreate, RestaurantUpdate
from flash.services.restaurant_service import RestaurantService

OWNER_ID = 1
OTHER_ACTOR_ID = 2


def a_restaurant(owner_id: int) -> RestaurantModel:
    return RestaurantModel(
        owner_id=owner_id,
        name="Test Place",
        address="123 Test St",
        phone="555-0000",
        email="place@example.com",
    )


class FakeRestaurantRepository:
    """In-memory stand-in — satisfies RestaurantRepoProtocol structurally."""

    def __init__(self) -> None:
        self._restaurants: dict[int, RestaurantModel] = {}
        self._next_id = 1
        self.commit_calls = 0

    def seed(self, restaurant: RestaurantModel) -> RestaurantModel:
        restaurant.id = self._next_id
        self._next_id += 1
        self._restaurants[restaurant.id] = restaurant
        return restaurant

    async def get(self, id: int) -> RestaurantModel | None:
        return self._restaurants.get(id)

    async def list(self, limit: int, offset: int) -> list[RestaurantModel]:
        return list(self._restaurants.values())[offset : offset + limit]

    async def create(self, instance: RestaurantModel) -> RestaurantModel:
        return self.seed(instance)

    async def delete(self, instance: RestaurantModel) -> None:
        self._restaurants.pop(instance.id, None)

    async def commit(self) -> None:
        self.commit_calls += 1


@pytest.fixture
def repo() -> FakeRestaurantRepository:
    return FakeRestaurantRepository()


@pytest.fixture
def service(repo: FakeRestaurantRepository) -> RestaurantService:
    return RestaurantService(repo)


class TestGet:
    async def test_raises_not_found_when_missing(
        self, service: RestaurantService
    ) -> None:
        with pytest.raises(RestaurantNotFound):
            await service.get(999)

    async def test_reads_are_not_scoped_to_the_owner(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        """The deliberate asymmetry with orders: anyone authenticated may read
        any restaurant, so get() takes no actor to check against."""
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        assert await service.get(seeded.id) is seeded


class TestList:
    async def test_returns_restaurants_owned_by_anyone(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        mine = repo.seed(a_restaurant(owner_id=OWNER_ID))
        theirs = repo.seed(a_restaurant(owner_id=OTHER_ACTOR_ID))
        listed = [r.id for r in await service.list(50, 0)]
        assert listed == [mine.id, theirs.id]


class TestCreate:
    async def test_owner_is_the_actor(self, service: RestaurantService) -> None:
        created = await service.create(
            RestaurantCreate(name="New Place", address="456 Main St"),
            OWNER_ID,
        )
        assert created.owner_id == OWNER_ID


class TestUpdate:
    async def test_owner_can_update(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        updated = await service.update(
            seeded.id, RestaurantUpdate(name="Renamed"), OWNER_ID
        )
        assert updated.name == "Renamed"

    async def test_non_owner_is_forbidden(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        """Forbidden, not RestaurantNotFound: the restaurant is readable by
        anyone, so pretending it does not exist would be a lie that hides
        nothing."""
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        with pytest.raises(Forbidden):
            await service.update(
                seeded.id, RestaurantUpdate(name="Hijacked"), OTHER_ACTOR_ID
            )
        assert seeded.name == "Test Place"

    async def test_missing_restaurant_is_not_found_before_ownership(
        self, service: RestaurantService
    ) -> None:
        """Existence is resolved first, so a bad id is a 404 rather than a 403
        -- otherwise every nonexistent id would report as forbidden."""
        with pytest.raises(RestaurantNotFound):
            await service.update(999, RestaurantUpdate(name="X"), OWNER_ID)

    async def test_blank_values_are_applied_not_skipped(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        """Regression test for the `or` idiom: `data.phone or restaurant.phone`
        treats "" as "unset" and refuses to clear a field the caller blanked
        deliberately."""
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        updated = await service.update(seeded.id, RestaurantUpdate(phone=""), OWNER_ID)
        assert updated.phone == ""

    async def test_omitted_fields_are_left_alone(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        updated = await service.update(
            seeded.id, RestaurantUpdate(name="Renamed"), OWNER_ID
        )
        assert updated.address == "123 Test St"
        assert updated.phone == "555-0000"
        assert updated.email == "place@example.com"


class TestDelete:
    async def test_owner_can_delete(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        await service.delete(seeded.id, OWNER_ID)
        assert await repo.get(seeded.id) is None

    async def test_non_owner_is_forbidden(
        self, service: RestaurantService, repo: FakeRestaurantRepository
    ) -> None:
        seeded = repo.seed(a_restaurant(owner_id=OWNER_ID))
        with pytest.raises(Forbidden):
            await service.delete(seeded.id, OTHER_ACTOR_ID)
        assert await repo.get(seeded.id) is seeded
