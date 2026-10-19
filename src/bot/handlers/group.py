import html
from collections.abc import Callable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TgUser

from src.bot.filters import IsGroup
from src.bot.keyboards import get_cancel_repeats_keyboard, get_language_keyboard
from src.db.models import User
from src.db.repositories import GroupRepository, SubscriptionRepository
from src.services.notification import GmResult, notification_service
from src.services.pushover import pushover_client

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


async def _gm_allowed(message: Message, _: Callable) -> bool:
    """Apply the group's only_admin restriction."""
    if await GroupRepository.is_only_admin(message.chat.id) and not await is_admin(message):
        await message.reply(_("gm_admin_only"))
        return False
    return True


def _reply_target(message: Message) -> TgUser | None:
    """Author of the replied message, ignoring bots and the forum topic root."""
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot or reply.forum_topic_created:
        return None
    return reply.from_user


async def _resolve_target(rest: str, group_id: int) -> tuple[int | None, str | None]:
    """Parse '<@username|user_id|username> [text]'.

    Returns (user_id, text); user_id is None if the first word names nobody here.
    """
    parts = rest.split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else None
    if parts[0].isdigit():
        return int(parts[0]), text
    found = await SubscriptionRepository.get_enabled_user_by_username(
        parts[0].removeprefix("@"), group_id
    )
    return (found[0] if found else None), text


# Forwarded commands come from someone else's chat history, never act on them
@router.message(Command("gm"), F.forward_origin.is_(None))
async def cmd_gm(message: Message, _: Callable) -> None:
    if not await _gm_allowed(message, _):
        return

    # Parse arguments: /gm [target] [custom_text]
    args = message.text.split(maxsplit=1)
    if len(args) <= 1:
        return await _gm_all(message, _)

    rest = args[1].strip()
    target_id, text = await _resolve_target(rest, message.chat.id)
    if target_id is not None:
        return await _gm_user(message, _, target_id, text)
    if rest.startswith("@"):
        await message.reply(_("gm_user_not_found"))
        return

    # The first word names nobody → the entire rest is custom text for all
    return await _gm_all(message, _, rest)


@router.message(Command("pgm"), F.forward_origin.is_(None))
async def cmd_pgm(message: Message, _: Callable) -> None:
    """Personal alert: needs a target and never falls back to the whole group."""
    if not await _gm_allowed(message, _):
        return

    args = message.text.split(maxsplit=1)
    rest = args[1].strip() if len(args) > 1 else ""

    reply_target = _reply_target(message)
    if reply_target:
        return await _gm_user(message, _, reply_target.id, rest or None)
    if not rest:
        await message.reply(_("pgm_usage"))
        return

    target_id, text = await _resolve_target(rest, message.chat.id)
    if target_id is None:
        await message.reply(_("gm_user_not_found"))
        return
    return await _gm_user(message, _, target_id, text)


async def _gm_all(message: Message, _: Callable, text: str | None = None) -> None:
    """Send GM to all enabled users in group."""
    sender = message.from_user
    if not await SubscriptionRepository.get_recipients(message.chat.id, sender.id):
        await message.reply(_("gm_no_users"))
        return

    status = await message.reply(_("gm_sending"))
    await _send_all_and_report(status, sender.id, sender.full_name, text, _)


async def _send_all_and_report(
    status: Message, sender_id: int, sender_name: str, text: str | None, _: Callable
) -> None:
    result = await notification_service.send_gm_to_all(
        group_id=status.chat.id,
        sender_id=sender_id,
        sender_name=sender_name,
        message=text,
    )
    await _report(status, result, sender_id, _)


async def _gm_user(message: Message, _: Callable, target_user_id: int, text: str | None) -> None:
    """Send GM to a specific user by ID."""
    status = await message.reply(_("gm_sending"))
    result = await notification_service.send_gm_to_user(
        group_id=message.chat.id,
        sender_id=message.from_user.id,
        target_user_id=target_user_id,
        sender_name=message.from_user.full_name,
        message=text,
    )
    await _report(status, result, message.from_user.id, _)


async def _report(status: Message, result: GmResult, sender_id: int, _: Callable) -> None:
    """Turn the 'sending' message into the result, with a cancel button while alerts repeat."""
    if result.refusal:
        text = _(result.refusal)
    elif result.fail == 0:
        text = _("gm_sent")
    elif result.success == 0:
        text = _("gm_user_failed", error=html.escape(result.error or ""))
    else:
        text = _("gm_sent_stats", success=result.success, fail=result.fail)

    if result.quiet_names:
        text += "\n" + _("gm_quiet_list", names=html.escape(", ".join(result.quiet_names)))

    markup = None
    if result.tag:
        markup = get_cancel_repeats_keyboard(_("btn_cancel_repeats"), sender_id, result.tag)
    await status.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith("gmc:"))
async def process_cancel_repeats(callback: CallbackQuery, _: Callable) -> None:
    """Stop Pushover retries of an alert; only its sender may do it."""
    _prefix, sender_id, tag = callback.data.split(":")
    if callback.from_user.id != int(sender_id):
        await callback.answer(_("cancel_not_yours"), show_alert=True)
        return

    if not await pushover_client.cancel_by_tag(tag):
        await callback.answer(_("cancel_failed"), show_alert=True)
        return

    await callback.message.edit_text(
        f"{callback.message.html_text}\n{_('cancel_done')}", reply_markup=None
    )
    await callback.answer()


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
