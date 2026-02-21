import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db.session import engine, sessionmaker
from bot.db.models import Base
from bot.middlewares.auth import AuthMiddleware
from bot.handlers import admin, labeling
from bot.services.cleanup import cleanup_stale_locks
from bot.services.redis import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admins from config
    if settings.admin_ids:
        from bot.db.models import User
        async with sessionmaker() as session:
            for admin_id in settings.admin_ids:
                existing = await session.get(User, admin_id)
                if existing is None:
                    session.add(User(telegram_id=admin_id, is_admin=True))
                elif not existing.is_admin:
                    existing.is_admin = True
            await session.commit()
        log.info("Seeded %d admin(s)", len(settings.admin_ids))

    asyncio.create_task(cleanup_stale_locks(sessionmaker))
    log.info("DB tables ensured")


async def on_shutdown() -> None:
    await redis.aclose()
    await engine.dispose()
    log.info("Connections closed")


async def main() -> None:
    bot = Bot(token=settings.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.update.middleware(AuthMiddleware(sessionmaker))

    dp.include_router(admin.router)
    dp.include_router(labeling.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    log.info("Starting bot…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
