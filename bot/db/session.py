from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import settings

engine = create_async_engine(settings.database_url, echo=False)
sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
