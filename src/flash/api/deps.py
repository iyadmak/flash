"""API Dependencies"""

from typing import Annotated, Any
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from pymongo.asynchronous.collection import AsyncCollection

from flash.core.db import get_async_session
from flash.core.config import Settings, get_settings
from flash.core.adapters import (
    CacheProtocol,
    LockProtocol,
    EventPublisherProtocol,
    KafkaEventStreamPublisher,
    KafkaEventStreamPublisherProtocol,
    get_lock_client,
    get_event_publisher,
    get_user_cache,
    get_daily_reports_collection,
)
from flash.schemas.user_schema import UserRead
from flash.services import (
    UserService,
    RestaurantService,
    OrderService,
    ItemService,
    AuthService,
    AnalyticsService,
)
from flash.repositories import (
    ItemRepository,
    OrderRepository,
    RestaurantRepository,
    UserRepository,
    PasswordResetTokenRepository,
)


# ------------------- General dependencies -------------------
def get_event_stream_publisher(request: Request) -> KafkaEventStreamPublisherProtocol:
    return KafkaEventStreamPublisher(request.app.state.kafka_producer)


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CacheDep = Annotated[CacheProtocol, Depends(get_user_cache)]
LockClientDep = Annotated[LockProtocol, Depends(get_lock_client)]
EventPublisherDep = Annotated[EventPublisherProtocol, Depends(get_event_publisher)]
EventStreamPublisherDep = Annotated[
    KafkaEventStreamPublisherProtocol, Depends(get_event_stream_publisher)
]
DailyReportsCollectionDep = Annotated[
    AsyncCollection[dict[str, Any]], Depends(get_daily_reports_collection)
]


# ------------------- Repository dependencies -------------------
def get_password_reset_token_repository(
    session: DBSessionDep,
) -> PasswordResetTokenRepository:
    return PasswordResetTokenRepository(session)


def get_item_repository(session: DBSessionDep) -> ItemRepository:
    return ItemRepository(session)


def get_order_repository(session: DBSessionDep) -> OrderRepository:
    return OrderRepository(session)


def get_restaurant_repository(session: DBSessionDep) -> RestaurantRepository:
    return RestaurantRepository(session)


def get_user_repository(session: DBSessionDep) -> UserRepository:
    return UserRepository(session)


ItemRepoDep = Annotated[ItemRepository, Depends(get_item_repository)]
OrderRepoDep = Annotated[OrderRepository, Depends(get_order_repository)]
RestaurantRepoDep = Annotated[RestaurantRepository, Depends(get_restaurant_repository)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
PasswordResetTokenRepoDep = Annotated[
    PasswordResetTokenRepository, Depends(get_password_reset_token_repository)
]


# ------------------- Service dependencies -------------------
def get_auth_service(
    user_repo: UserRepoDep,
    reset_token_repo: PasswordResetTokenRepoDep,
    cache: CacheDep,
) -> AuthService:
    return AuthService(user_repo, reset_token_repo, cache)


def get_item_service(repo: ItemRepoDep) -> ItemService:
    return ItemService(repo)


def get_user_service(repo: UserRepoDep, cache: CacheDep) -> UserService:
    return UserService(repo, cache)


def get_restaurant_service(repo: RestaurantRepoDep) -> RestaurantService:
    return RestaurantService(repo)


def get_order_service(
    repo: OrderRepoDep,
    lock_client: LockClientDep,
    event_publisher: EventPublisherDep,
    event_stream_publisher: EventStreamPublisherDep,
) -> OrderService:
    return OrderService(repo, lock_client, event_publisher, event_stream_publisher)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


def get_analytics_service(
    daily_reports: DailyReportsCollectionDep, restaurant_service: RestaurantServiceDep
) -> AnalyticsService:
    return AnalyticsService(daily_reports, restaurant_service)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]

# ------------------- auth dependencies -------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], auth_service: AuthServiceDep
) -> UserRead:
    return await auth_service.get_current_user(token)


CurrentUserDep = Annotated[UserRead, Depends(get_current_user)]
