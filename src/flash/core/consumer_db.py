from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from flash.core.config import get_settings

# NullPool: each asyncio.run() in the consumer gets a fresh connection and
# closes it before the loop tears down. A pooled connection checked back in
# from a dead loop would blow up as "Event loop is closed" on next checkout.
consumer_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
consumer_session_maker = async_sessionmaker(consumer_engine, expire_on_commit=False)
