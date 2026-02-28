import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Item, Label
from bot.services.lock import acquire_item_lock, clear_user_current, release_item_lock

log = logging.getLogger(__name__)


async def get_next_task(session: AsyncSession, user_id: int) -> Item | None:
    # Find a pending item not yet labeled/skipped by this user
    subq = select(Label.item_id).where(Label.user_id == user_id).scalar_subquery()

    stmt = (
        select(Item)
        .where(Item.status == "pending", Item.id.notin_(subq))
        .order_by(Item.created_at.desc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    item = (await session.execute(stmt)).scalar_one_or_none()
    if item is None:
        return None

    acquired = await acquire_item_lock(item.id, user_id)
    if not acquired:
        return None

    item.status = "locked"
    await session.commit()

    return item


async def complete_task(
    session: AsyncSession, item_id: int, user_id: int, score: int | None, action: str
) -> None:
    new_status = "labeled" if action == "rated" else "skipped"

    await session.execute(update(Item).where(Item.id == item_id).values(status=new_status))

    label = Label(item_id=item_id, user_id=user_id, score=score, action=action)
    session.add(label)
    await session.commit()

    await release_item_lock(item_id)
    await clear_user_current(user_id)
