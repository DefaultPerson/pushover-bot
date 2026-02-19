from typing import Callable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.bot.filters import IsGroup
from src.bot.keyboards import get_language_keyboard
from src.db.models import User
from src.db.repositories import GroupRepository, SubscriptionRepository
from src.services.notification import notification_service

router = Router()
router.message.filter(IsGroup())


async def is_admin(message: Message) -> bool:
    """Check if user is admin in the chat."""
    if message.chat.type == "private":
        return True

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ("administrator", "creator")


@router.message(Command("enable"))
async def cmd_enable(message: Message, db_user: User, _: Callable) -> None:
    if not db_user.pushover_key:
        await message.reply(_("enable_no_key"))
        return

    await SubscriptionRepository.enable(message.from_user.id, message.chat.id)
    await message.reply(_("enable_success"))


@router.message(Command("disable"))
async def cmd_disable(message: Message, _: Callable) -> None:
    await SubscriptionRepository.disable(message.from_user.id, message.chat.id)
    await message.reply(_("disable_success"))


@router.message(Command("gm"))
async def cmd_gm(message: Message, _: Callable) -> None:
    # Check only_admin restriction
    only_admin = await GroupRepository.is_only_admin(message.chat.id)
    if only_admin and not await is_admin(message):
        await message.reply(_("gm_admin_only"))
        return

    group_id = message.chat.id
    sender_id = message.from_user.id
    sender_name = message.from_user.full_name

    # Parse arguments: /gm [target] [custom_text]
    args = message.text.split(maxsplit=1)

    if len(args) <= 1:
        # /gm → send to all with default text
        return await _send_to_all(message, group_id, sender_id, sender_name, _)

    rest = args[1].strip()

    # 1. Starts with @ → username target
    if rest.startswith("@"):
        parts = rest[1:].split(maxsplit=1)
        username = parts[0]
        custom_text = parts[1] if len(parts) > 1 else None
        return await _resolve_and_send_to_user(
            message, group_id, sender_id, sender_name, _, username=username, custom_text=custom_text
        )

    # 2. Parse first word
    parts = rest.split(maxsplit=1)
    first_word = parts[0]
    remaining = parts[1] if len(parts) > 1 else None

    # 3. Numeric ID → send to user by ID
    if first_word.isdigit():
        return await _send_to_user(
            message, group_id, sender_id, sender_name, _,
            target_user_id=int(first_word), custom_text=remaining,
        )

    # 4. Try to find as username among group subscribers
    found = await SubscriptionRepository.get_enabled_user_by_username(first_word, group_id)
    if found:
        return await _send_to_user(
            message, group_id, sender_id, sender_name, _,
            target_user_id=found[0], custom_text=remaining,
        )

    # 5. Not found → entire rest is custom text for all
    return await _send_to_all(message, group_id, sender_id, sender_name, _, custom_text=rest)


async def _send_to_all(
    msg: Message,
    group_id: int,
    sender_id: int,
    sender_name: str,
    _: Callable,
    *,
    custom_text: str | None = None,
) -> None:
    """Send GM to all enabled users in group."""
    users = await SubscriptionRepository.get_enabled_users_with_keys(group_id)

    if not users:
        await msg.reply(_("gm_no_users"))
        return

    await msg.reply(_("gm_sending"))

    success, fail = await notification_service.send_gm_to_all(
        group_id=group_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message=custom_text,
    )

    if fail == 0:
        await msg.reply(_("gm_sent"))
    else:
        await msg.reply(_("gm_sent_stats", success=success, fail=fail))


async def _send_to_user(
    msg: Message,
    group_id: int,
    sender_id: int,
    sender_name: str,
    _: Callable,
    *,
    target_user_id: int,
    custom_text: str | None = None,
) -> None:
    """Send GM to a specific user by ID."""
    await msg.reply(_("gm_sending"))

    ok, error = await notification_service.send_gm_to_user(
        group_id=group_id,
        sender_id=sender_id,
        target_user_id=target_user_id,
        sender_name=sender_name,
        message=custom_text,
    )

    if ok:
        await msg.reply(_("gm_user_sent"))
    else:
        await msg.reply(_("gm_user_failed", error=error))


async def _resolve_and_send_to_user(
    msg: Message,
    group_id: int,
    sender_id: int,
    sender_name: str,
    _: Callable,
    *,
    username: str,
    custom_text: str | None = None,
) -> None:
    """Resolve username to user_id and send GM."""
    found = await SubscriptionRepository.get_enabled_user_by_username(username, group_id)
    if not found:
        await msg.reply(_("gm_user_not_found"))
        return

    await _send_to_user(
        msg, group_id, sender_id, sender_name, _,
        target_user_id=found[0], custom_text=custom_text,
    )


@router.message(Command("only_admin"))
async def cmd_only_admin(message: Message, _: Callable) -> None:
    if not await is_admin(message):
        await message.reply(_("only_admin_permission"))
        return

    new_value = await GroupRepository.toggle_only_admin(message.chat.id)

    if new_value:
        await message.reply(_("only_admin_enabled"))
    else:
        await message.reply(_("only_admin_disabled"))


@router.message(Command("language"))
async def cmd_language_group(message: Message, _: Callable) -> None:
    """Change group language (admin only)."""
    if not await is_admin(message):
        await message.reply(_("only_admin_permission"))
        return

    await message.reply(_("language_select"), reply_markup=get_language_keyboard())


@router.callback_query(
    F.data.startswith("lang:"),
    F.message.chat.type.in_({"group", "supergroup"}),
)
async def process_group_language(callback: CallbackQuery, _: Callable) -> None:
    """Process group language selection callback (admin only)."""

    # Check admin permission
    member = await callback.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ("administrator", "creator"):
        await callback.answer(_("only_admin_permission"), show_alert=True)
        return

    lang = callback.data.split(":")[1]
    await GroupRepository.set_language(callback.message.chat.id, lang)

    # Update command menu for this group
    from aiogram.types import BotCommandScopeChat
    from src.bot.commands import GROUP_COMMANDS

    commands = GROUP_COMMANDS.get(lang, GROUP_COMMANDS["en"])
    await callback.bot.set_my_commands(
        commands,
        scope=BotCommandScopeChat(chat_id=callback.message.chat.id),
    )

    from src.i18n import get_text

    await callback.message.edit_text(get_text("group_language_changed", lang))
    await callback.answer()
