import html
import json
from collections.abc import Callable

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

from src.bot.filters import IsGroup, ViaThisBot
from src.bot.keyboards import (
    get_cancel_repeats_keyboard,
    get_confirm_gm_keyboard,
    get_language_keyboard,
)
from src.bot.utils import button_is_real, reply_target
from src.config import settings
from src.db.models import User
from src.db.repositories import (
    GroupRepository,
    NotificationLogRepository,
    SubscriptionRepository,
)
from src.services.notification import GmResult, notification_service
from src.services.pushover import pushover_client

log = structlog.get_logger()

router = Router()
router.message.filter(IsGroup())

# Seconds a /confirm_gm request waits for the sender's answer
CONFIRM_TTL = 120


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
async def cmd_gm(message: Message, _: Callable, redis: Redis) -> None:
    if not await _gm_allowed(message, _):
        return

    # Parse arguments: /gm [target] [custom_text]
    args = message.text.split(maxsplit=1)
    if len(args) <= 1:
        return await _gm_all(message, _, redis)

    rest = args[1].strip()
    target_id, text = await _resolve_target(rest, message.chat.id)
    if target_id is not None:
        return await _gm_user(message, _, target_id, text)
    if rest.startswith("@"):
        await message.reply(_("gm_user_not_found"))
        return

    # The first word names nobody → the entire rest is custom text for all
    return await _gm_all(message, _, redis, rest)


@router.message(Command("pgm"), F.forward_origin.is_(None))
async def cmd_pgm(message: Message, _: Callable) -> None:
    """Personal alert: needs a target and never falls back to the whole group."""
    if not await _gm_allowed(message, _):
        return

    args = message.text.split(maxsplit=1)
    rest = args[1].strip() if len(args) > 1 else ""

    target = reply_target(message)
    if target:
        return await _gm_user(message, _, target.id, rest or None)
    if not rest:
        await message.reply(_("pgm_usage"))
        return

    target_id, text = await _resolve_target(rest, message.chat.id)
    if target_id is None:
        await message.reply(_("gm_user_not_found"))
        return
    return await _gm_user(message, _, target_id, text)


def _inline_target(message: Message) -> str | None:
    """'all' or a user id, from the button the inline result was posted with."""
    markup = message.reply_markup
    if not markup or not markup.inline_keyboard or not markup.inline_keyboard[0]:
        return None
    data = markup.inline_keyboard[0][0].callback_data or ""
    target = data.removeprefix("ig:")
    if data.startswith("ig:") and (target == "all" or target.isdigit()):
        return target
    return None


@router.message(ViaThisBot(), F.forward_origin.is_(None))
async def on_inline_gm(message: Message, _: Callable, redis: Redis) -> None:
    """An alert the sender posted from '@bot' inline results (see handlers/inline.py)."""
    target = _inline_target(message)
    # target is None when Telegram dropped the result's button
    log.info(
        "Inline alert", group_id=message.chat.id, sender_id=message.from_user.id, target=target
    )
    if target is None or not await _gm_allowed(message, _):
        return

    # First line is the header the bot generated, the rest is the sender's text
    lines = (message.text or "").split("\n", 1)
    text = lines[1].strip() if len(lines) > 1 else ""
    if target == "all":
        return await _gm_all(message, _, redis, text or None)
    return await _gm_user(message, _, int(target), text or None)


def _confirm_key(message: Message) -> str:
    return f"gm_confirm:{message.chat.id}:{message.message_id}"


async def _gm_all(message: Message, _: Callable, redis: Redis, text: str | None = None) -> None:
    """Send GM to all enabled users in group, after confirmation if the group wants it."""
    sender = message.from_user
    recipients = await SubscriptionRepository.get_recipients(message.chat.id, sender.id)
    if not recipients:
        await message.reply(_("gm_no_users"))
        return

    if await GroupRepository.is_confirm_gm(message.chat.id):
        prompt = await message.reply(
            _("confirm_prompt", count=len(recipients)),
            reply_markup=get_confirm_gm_keyboard(
                _("btn_confirm_yes"), _("btn_confirm_no"), sender.id
            ),
        )
        pending = json.dumps({"name": sender.full_name, "text": text})
        await redis.set(_confirm_key(prompt), pending, ex=CONFIRM_TTL)
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


@router.callback_query(F.data.startswith(("gmy:", "gmn:")))
async def process_gm_confirm(callback: CallbackQuery, _: Callable, redis: Redis) -> None:
    """Answer to 'Wake N people?'; only the sender may answer."""
    action, sender_id = callback.data.split(":")
    if not button_is_real(callback) or callback.from_user.id != int(sender_id):
        await callback.answer(_("confirm_not_yours"), show_alert=True)
        return

    # Whoever deletes the key owns the request, so a double tap can't send twice
    key = _confirm_key(callback.message)
    pending = await redis.get(key)
    if pending is not None and not await redis.delete(key):
        pending = None
    await callback.answer()

    if action == "gmn":
        await callback.message.edit_text(_("confirm_cancelled"))
        return
    if pending is None:
        await callback.message.edit_text(_("confirm_expired"))
        return

    # Several prompts may wait at once; the limit counts only sent alerts
    allowed = await NotificationLogRepository.check_gm_rate_limit(
        group_id=callback.message.chat.id,
        window_seconds=settings.gm_rate_window,
        max_calls=settings.gm_rate_limit,
    )
    if not allowed:
        await callback.message.edit_text(_("rate_limit_gm"))
        return

    data = json.loads(pending)
    await callback.message.edit_text(_("gm_sending"))
    await _send_all_and_report(callback.message, int(sender_id), data["name"], data["text"], _)


@router.callback_query(F.data.startswith("gmc:"))
async def process_cancel_repeats(callback: CallbackQuery, _: Callable) -> None:
    """Stop Pushover retries of an alert; only its sender may do it."""
    _prefix, sender_id, tag = callback.data.split(":")
    if not button_is_real(callback) or callback.from_user.id != int(sender_id):
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


@router.message(Command("confirm_gm"))
async def cmd_confirm_gm(message: Message, _: Callable) -> None:
    if not await is_admin(message):
        await message.reply(_("only_admin_permission"))
        return

    new_value = await GroupRepository.toggle_confirm_gm(message.chat.id)
    await message.reply(_("confirm_gm_enabled" if new_value else "confirm_gm_disabled"))


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
    from src.bot.commands import apply_group_menu

    await apply_group_menu(callback.bot, callback.message.chat.id, lang)

    from src.i18n import get_text

    await callback.message.edit_text(get_text("group_language_changed", lang))
    await callback.answer()
