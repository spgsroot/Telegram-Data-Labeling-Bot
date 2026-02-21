from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class LabelCB(CallbackData, prefix="lbl"):
    action: str  # "rate" or "skip"
    score: int  # 0-10 (ignored when action=skip)
    item_id: int


# Red → Orange → Yellow → Green gradient
_SCORE_EMOJI = ["🟢", "🟢", "🟢", "🟢", "🟡", "🟡", "🟡", "🟠", "🟠", "🔴", "🔴"]


def get_labeling_keyboard(item_id: int) -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(
            text=f"{_SCORE_EMOJI[i]} {i}",
            callback_data=LabelCB(action="rate", score=i, item_id=item_id).pack(),
        )
        for i in range(6)
    ]
    row2 = [
        InlineKeyboardButton(
            text=f"{_SCORE_EMOJI[i]} {i}",
            callback_data=LabelCB(action="rate", score=i, item_id=item_id).pack(),
        )
        for i in range(6, 11)
    ]
    row3 = [
        InlineKeyboardButton(
            text="⏭ Пропустить",
            callback_data=LabelCB(action="skip", score=0, item_id=item_id).pack(),
        )
    ]

    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3])
