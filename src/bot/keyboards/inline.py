from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


def get_cancel_keyboard(text: str = "Cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="cancel")]]
    )


def get_groups_keyboard(groups: list[tuple[int, str, bool]]) -> InlineKeyboardMarkup:
    """Create keyboard with group buttons showing status.

    Args:
        groups: List of (group_id, title, bot_active) tuples.

    Returns:
        InlineKeyboardMarkup with each group as a button row.
    """
    keyboard = []
    for group_id, title, bot_active in groups:
        status_emoji = "\u2705" if bot_active else "\u274c"
        button_text = f"{title} {status_emoji}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"group:{group_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_repeats_keyboard(text: str, sender_id: int, tag: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"gmc:{sender_id}:{tag}")]]
    )


def get_confirm_gm_keyboard(yes: str, no: str, sender_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=yes, callback_data=f"gmy:{sender_id}"),
                InlineKeyboardButton(text=no, callback_data=f"gmn:{sender_id}"),
            ]
        ]
    )


def get_inline_gm_keyboard(target: str) -> InlineKeyboardMarkup:
    """Button on a message posted from inline results; its data tells the bot whom to wake."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚨", callback_data=f"ig:{target}")]]
    )
