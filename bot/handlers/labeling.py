import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import Label, User
from bot.keyboards import LabelCB, get_labeling_keyboard
from bot.services.items import complete_task, get_next_task
from bot.services.lock import get_user_current, set_user_current

log = logging.getLogger(__name__)
router = Router(name="labeling")


async def _send_task(
    bot: Bot, chat_id: int, user_id: int, session_factory: async_sessionmaker
) -> None:
    async with session_factory() as session:
        item = await get_next_task(session, user_id)

    if item is None:
        await bot.send_message(chat_id, "Задач пока нет, возвращайтесь позже.")
        return

    msg = await bot.send_message(
        chat_id,
        f"📝 <b>Оцените текст (0-10):</b>\n\n{item.text}",
        reply_markup=get_labeling_keyboard(item.id),
    )
    await set_user_current(user_id, item.id, msg.message_id)


@router.message(Command("start"))
async def handle_start(
    message: Message, bot: Bot, db_user: User, session_factory: async_sessionmaker
) -> None:
    # Check if user already has an active task
    current_item_id, current_msg_id = await get_user_current(db_user.telegram_id)
    if current_item_id is not None:
        # Re-show the current task by deleting old message and resending
        if current_msg_id is not None:
            try:
                await bot.delete_message(message.chat.id, current_msg_id)
            except Exception:
                pass

        async with session_factory() as session:
            from bot.db.models import Item

            item = await session.get(Item, current_item_id)

        if item is not None:
            msg = await message.answer(
                f"📝 <b>Оцените текст (0-10):</b>\n\n{item.text}",
                reply_markup=get_labeling_keyboard(item.id),
            )
            await set_user_current(db_user.telegram_id, item.id, msg.message_id)
            return

    await _send_task(bot, message.chat.id, db_user.telegram_id, session_factory)


@router.callback_query(LabelCB.filter())
async def handle_label_callback(
    callback: CallbackQuery,
    callback_data: LabelCB,
    bot: Bot,
    db_user: User,
    session_factory: async_sessionmaker,
) -> None:
    await callback.answer()

    action = "rated" if callback_data.action == "rate" else "skipped"
    score = callback_data.score if action == "rated" else None

    try:
        async with session_factory() as session:
            await complete_task(
                session, callback_data.item_id, db_user.telegram_id, score, action
            )
    except Exception:
        log.exception("Error completing task item_id=%d", callback_data.item_id)
        await callback.message.edit_text("Произошла ошибка. Попробуйте /start.")  # type: ignore[union-attr]
        return

    # Delete the labeling message
    try:
        await callback.message.delete()  # type: ignore[union-attr]
    except Exception:
        log.warning(
            "Could not delete message %s",
            callback.message.message_id if callback.message else "?",
        )

    # Send next task immediately
    await _send_task(bot, callback.from_user.id, db_user.telegram_id, session_factory)


# ── Personal stats ────────────────────────────────────────────────────


@router.message(Command("stats"))
async def handle_stats(
    message: Message, db_user: User, session_factory: async_sessionmaker
) -> None:
    async with session_factory() as session:
        rated_count = (
            await session.execute(
                select(func.count(Label.item_id)).where(
                    Label.user_id == db_user.telegram_id, Label.action == "rated"
                )
            )
        ).scalar() or 0

        skipped_count = (
            await session.execute(
                select(func.count(Label.item_id)).where(
                    Label.user_id == db_user.telegram_id, Label.action == "skipped"
                )
            )
        ).scalar() or 0

        avg_time = (
            await session.execute(
                select(func.avg(func.extract("epoch", Label.created_at))).where(
                    Label.user_id == db_user.telegram_id, Label.action == "rated"
                )
            )
        ).scalar()

    await message.answer(
        f"📊 <b>Ваша статистика</b>\n\n"
        f"Размечено: <b>{rated_count}</b>\n"
        f"Пропущено: <b>{skipped_count}</b>"
    )
