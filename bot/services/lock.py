import logging

from bot.config import settings
from bot.services.redis import redis

log = logging.getLogger(__name__)

LOCK_PREFIX = "lock:item:"
CURRENT_ITEM_PREFIX = "user:current_item:"
CURRENT_MSG_PREFIX = "user:current_msg:"


async def acquire_item_lock(item_id: int, user_id: int) -> bool:
    key = f"{LOCK_PREFIX}{item_id}"
    acquired = await redis.set(key, str(user_id), nx=True, ex=settings.lock_ttl_seconds)
    return acquired is not None


async def release_item_lock(item_id: int) -> None:
    await redis.delete(f"{LOCK_PREFIX}{item_id}")


async def get_lock_owner(item_id: int) -> int | None:
    val = await redis.get(f"{LOCK_PREFIX}{item_id}")
    return int(val) if val else None


async def set_user_current(user_id: int, item_id: int, message_id: int) -> None:
    await redis.set(f"{CURRENT_ITEM_PREFIX}{user_id}", str(item_id))
    await redis.set(f"{CURRENT_MSG_PREFIX}{user_id}", str(message_id))


async def get_user_current(user_id: int) -> tuple[int | None, int | None]:
    item_raw = await redis.get(f"{CURRENT_ITEM_PREFIX}{user_id}")
    msg_raw = await redis.get(f"{CURRENT_MSG_PREFIX}{user_id}")
    item_id = int(item_raw) if item_raw else None
    msg_id = int(msg_raw) if msg_raw else None
    return item_id, msg_id


async def clear_user_current(user_id: int) -> None:
    await redis.delete(f"{CURRENT_ITEM_PREFIX}{user_id}", f"{CURRENT_MSG_PREFIX}{user_id}")
