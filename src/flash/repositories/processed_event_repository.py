from sqlalchemy.ext.asyncio import AsyncSession
from flash.repositories.base import BaseRepository
from flash.models.processed_event_model import ProcessedEventModel


class ProcessedEventRepository(BaseRepository[ProcessedEventModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProcessedEventModel)
