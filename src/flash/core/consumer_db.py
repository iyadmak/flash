from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from flash.core.config import get_settings

# NullPool: the consumer's asyncio.run() per message would otherwise check a
# connection back in from a dead loop and fail with "Event loop is closed".
consumer_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
consumer_session_maker = async_sessionmaker(consumer_engine, expire_on_commit=False)
