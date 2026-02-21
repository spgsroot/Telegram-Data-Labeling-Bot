import io
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.models import Item, Label, User
from bot.services.data import export_to_7z, import_from_7z

log = logging.getLogger(__name__)
router = Router(name="admin")

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _require_admin(user: User) -> bool:
    return user.is_admin


# ── Import: accept .7z document ──────────────────────────────────────

@router.message(F.document)
async def handle_document(message: Message, bot: Bot, db_user: User, session_factory: async_sessionmaker) -> None:
    if not _require_admin(db_user):
        await message.answer("Только администраторы могут загружать файлы.")
        return

    doc = message.document
    if not doc or not doc.file_name or not doc.file_name.endswith(".7z"):
        await message.answer("Принимаются только файлы формата <b>.7z</b>.")
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer(f"Файл слишком большой. Лимит: {MAX_FILE_SIZE // (1024 * 1024)} МБ.")
        return

    status_msg = await message.answer("⏳ Обрабатываю архив…")

    file = await bot.download(doc)
    if file is None:
        await status_msg.edit_text("Не удалось скачать файл.")
        return

    file_bytes = file.read()

    try:
        async with session_factory() as session:
            result = await import_from_7z(session, file_bytes)
    except ValueError as e:
        await status_msg.edit_text(f"Ошибка: {e}")
        return
    except Exception:
        log.exception("Import error")
        await status_msg.edit_text("Произошла ошибка при импорте.")
        return

    await status_msg.edit_text(
        f"✅ Импорт завершён.\n"
        f"Загружено: <b>{result.loaded}</b>\n"
        f"Дубликатов: <b>{result.duplicates}</b>\n"
        f"Ошибок: <b>{result.errors}</b>"
    )


# ── Export ────────────────────────────────────────────────────────────

@router.message(Command("export"))
async def handle_export(message: Message, db_user: User, session_factory: async_sessionmaker) -> None:
    if not _require_admin(db_user):
        await message.answer("Только администраторы могут экспортировать данные.")
        return

    status_msg = await message.answer("⏳ Формирую экспорт…")

    try:
        async with session_factory() as session:
            archive_bytes = await export_to_7z(session)
    except Exception:
        log.exception("Export error")
        await status_msg.edit_text("Произошла ошибка при экспорте.")
        return

    if archive_bytes is None:
        await status_msg.edit_text("Нет размеченных данных для экспорта.")
        return

    await status_msg.delete()
    await message.answer_document(
        BufferedInputFile(archive_bytes, filename="dataset_export.7z"),
        caption="📦 Экспорт завершён.",
    )


# ── Admin management ─────────────────────────────────────────────────

@router.message(Command("admin"))
async def handle_admin_command(
    message: Message, command: CommandObject, db_user: User, session_factory: async_sessionmaker
) -> None:
    if not _require_admin(db_user):
        await message.answer("Только администраторы могут использовать эту команду.")
        return

    args = command.args
    if not args:
        await message.answer(
            "Использование:\n"
            "/admin user add <user_id>\n"
            "/admin admin add <user_id>\n"
            "/admin stats"
        )
        return

    parts = args.split()

    if parts[0] == "stats":
        await _show_global_stats(message, session_factory)
        return

    if len(parts) == 3 and parts[1] == "add":
        role = parts[0]  # "user" or "admin"
        try:
            target_id = int(parts[2])
        except ValueError:
            await message.answer("user_id должен быть числом.")
            return

        async with session_factory() as session:
            user = await session.get(User, target_id)
            if user is None:
                user = User(telegram_id=target_id, is_admin=(role == "admin"))
                session.add(user)
            else:
                if role == "admin":
                    user.is_admin = True
            await session.commit()

        label = "администратор" if role == "admin" else "пользователь"
        await message.answer(f"✅ {label.capitalize()} <code>{target_id}</code> добавлен.")
        return

    await message.answer("Неизвестная подкоманда. Используйте /admin для справки.")


async def _show_global_stats(message: Message, session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        total = (await session.execute(select(func.count(Item.id)))).scalar() or 0
        labeled = (
            await session.execute(select(func.count(Item.id)).where(Item.status == "labeled"))
        ).scalar() or 0
        remaining = (
            await session.execute(
                select(func.count(Item.id)).where(Item.status.in_(["pending", "locked"]))
            )
        ).scalar() or 0

        per_user = (
            await session.execute(
                select(
                    Label.user_id,
                    func.count(Label.item_id).label("cnt"),
                )
                .where(Label.action == "rated")
                .group_by(Label.user_id)
            )
        ).all()

    lines = [
        f"📊 <b>Глобальная статистика</b>\n",
        f"Всего записей: <b>{total}</b>",
        f"Размечено: <b>{labeled}</b>",
        f"Осталось: <b>{remaining}</b>",
    ]
    if per_user:
        lines.append("\n<b>По пользователям:</b>")
        for uid, cnt in per_user:
            lines.append(f"  • <code>{uid}</code>: {cnt}")

    await message.answer("\n".join(lines))
