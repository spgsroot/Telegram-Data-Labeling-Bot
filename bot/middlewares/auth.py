import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import User

log = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update: Update = event  # type: ignore[assignment]

        user_tg = None
        if update.message:
            user_tg = update.message.from_user
        elif update.callback_query:
            user_tg = update.callback_query.from_user

        if user_tg is None:
            return

        async with self.session_factory() as session:
            user = await session.get(User, user_tg.id)

        if user is None:
            log.warning("Unauthorized access attempt: user_id=%d", user_tg.id)
            if update.message:
                await update.message.answer("Доступ запрещён.")
            elif update.callback_query:
                await update.callback_query.answer("Доступ запрещён.", show_alert=True)
            return

        data["db_user"] = user
        data["session_factory"] = self.session_factory
        return await handler(event, data)
