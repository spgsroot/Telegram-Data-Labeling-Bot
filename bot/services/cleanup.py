import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import Item
from bot.services.lock import LOCK_PREFIX
from bot.services.redis import redis

log = logging.getLogger(__name__)

CLEANUP_INTERVAL = 60  # seconds


async def cleanup_stale_locks(session_factory: async_sessionmaker) -> None:
    """Reset items stuck in 'locked' status whose Redis lock has expired."""
    while True:
        try:
            async with session_factory() as session:
                locked_items = (
                    await session.execute(select(Item.id).where(Item.status == "locked"))
                ).scalars().all()

                for item_id in locked_items:
                    key = f"{LOCK_PREFIX}{item_id}"
                    exists = await redis.exists(key)
                    if not exists:
                        await session.execute(
                            update(Item).where(Item.id == item_id).values(status="pending")
                        )
                        log.info("Reset stale lock for item_id=%d", item_id)

                await session.commit()
        except Exception:
            log.exception("Error in cleanup task")

        await asyncio.sleep(CLEANUP_INTERVAL)
