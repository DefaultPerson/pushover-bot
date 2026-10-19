import html
from collections.abc import Callable
from datetime import UTC, datetime

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.bot.filters import IsGroup, IsPrivate
from src.bot.utils import reply_target
from src.config import settings
from src.db.models import User
from src.db.repositories import BlockRepository, UserRepository
from src.services.notification import notification_service
from src.services.quiet import QuietParseError, get_zone, parse_quiet

router = Router()
log = structlog.get_logger()


@router.message(CommandStart(), IsPrivate())
async def cmd_start(message: Message, _: Callable) -> None:
    log.info("cmd_start", user_id=message.from_user.id)
    await message.answer(_("start"))


@router.message(Command("help"), IsPrivate())
async def cmd_help_private(message: Message, _: Callable) -> None:
    await message.answer(_("start"))


@router.message(Command("help"), IsGroup())
async def cmd_help_group(message: Message, _: Callable) -> None:
    await message.reply(_("start"))


@router.message(Command("test_alarm"))
async def cmd_test_alarm(message: Message, db_user: User, _: Callable) -> None:
    if not db_user.pushover_key:
        await message.reply(_("test_no_key"))
        return

    await message.reply(_("test_sending"))

    ok, error = await notification_service.send_test_alarm(message.from_user.id)

    if ok:
        await message.reply(_("test_success"))
    else:
        await message.reply(_("test_failed", error=error))


@router.message(Command("gm", "pgm"), IsPrivate())
async def cmd_gm_private(message: Message, _: Callable) -> None:
    await message.answer(_("only_group"))


def _format_dt(value: datetime, tz: str) -> str:
    return f"{value.astimezone(get_zone(tz)).strftime('%d.%m %H:%M')} ({tz})"


def _quiet_status(user: User, now: datetime, _: Callable) -> str:
    tz = user.quiet_tz or settings.default_timezone
    lines = []
    if user.quiet_start and user.quiet_end:
        lines.append(
            _(
                "quiet_status_daily",
                start=user.quiet_start.strftime("%H:%M"),
                end=user.quiet_end.strftime("%H:%M"),
                tz=tz,
            )
        )
    if user.quiet_from and user.quiet_to and user.quiet_to > now:
        lines.append(
            _(
                "quiet_status_period",
                start=_format_dt(user.quiet_from, tz),
                end=_format_dt(user.quiet_to, tz),
            )
        )
    return "\n".join(lines) or _("quiet_status_none")


@router.message(Command("quiet"))
async def cmd_quiet(message: Message, db_user: User, _: Callable) -> None:
    args = message.text.split(maxsplit=1)
    now = datetime.now(UTC)
    if len(args) <= 1:
        status = _quiet_status(db_user, now, _)
        await message.reply(f"{status}\n\n{_('quiet_usage', tz=settings.default_timezone)}")
        return

    try:
        change = parse_quiet(args[1], db_user.quiet_tz, now)
    except QuietParseError as e:
        await message.reply(_(e.args[0], tz=settings.default_timezone))
        return

    user_id = message.from_user.id
    if change.kind == "off":
        await UserRepository.clear_quiet(user_id)
        await message.reply(_("quiet_off"))
    elif change.kind == "daily":
        await UserRepository.set_quiet_daily(user_id, change.start, change.end, change.tz)
        await message.reply(
            _(
                "quiet_daily_set",
                start=change.start.strftime("%H:%M"),
                end=change.end.strftime("%H:%M"),
                tz=change.tz,
            )
        )
    else:
        await UserRepository.set_quiet_period(
            user_id, change.quiet_from, change.quiet_to, change.tz
        )
        tz = change.tz or db_user.quiet_tz or settings.default_timezone
        await message.reply(
            _(
                "quiet_period_set",
                start=_format_dt(change.quiet_from, tz),
                end=_format_dt(change.quiet_to, tz),
            )
        )


@router.message(Command("personalgms"))
async def cmd_personalgms(message: Message, db_user: User, _: Callable) -> None:
    args = message.text.split(maxsplit=1)
    arg = args[1].strip().lower() if len(args) > 1 else ""
    if arg not in ("on", "off"):
        key = "personalgms_status_on" if db_user.personal_gms else "personalgms_status_off"
        await message.reply(_(key))
        return

    enabled = arg == "on"
    await UserRepository.set_personal_gms(message.from_user.id, enabled)
    await message.reply(_("personalgms_on" if enabled else "personalgms_off"))


async def _block_target(message: Message, _: Callable) -> tuple[int, str] | None:
    """Whom /block or /unblock is about: the replied author, or @username / id in the arguments."""
    target = reply_target(message)
    if target:
        return target.id, target.full_name

    args = message.text.split(maxsplit=1)
    arg = args[1].strip() if len(args) > 1 else ""
    if arg.isdigit():
        return int(arg), arg
    if arg:
        user = await UserRepository.get_by_username(arg.removeprefix("@"))
        if user:
            return user.id, user.display_name
        await message.reply(_("block_unknown_user"))
        return None

    await message.reply(_("block_usage"))
    return None


@router.message(Command("block"))
async def cmd_block(message: Message, _: Callable) -> None:
    target = await _block_target(message, _)
    if not target:
        return
    target_id, name = target
    if target_id == message.from_user.id:
        await message.reply(_("block_self"))
        return

    await BlockRepository.add(message.from_user.id, target_id)
    await message.reply(_("block_done", name=html.escape(name)))


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, _: Callable) -> None:
    target = await _block_target(message, _)
    if not target:
        return
    target_id, name = target

    removed = await BlockRepository.remove(message.from_user.id, target_id)
    await message.reply(_("unblock_done" if removed else "unblock_missing", name=html.escape(name)))


@router.message(Command("blocks"))
async def cmd_blocks(message: Message, _: Callable) -> None:
    blocked = await BlockRepository.get_blocked(message.from_user.id)
    if not blocked:
        await message.reply(_("blocks_empty"))
        return

    lines = [_("blocks_header")]
    for user_id, full_name, username in blocked:
        name = full_name or (f"@{username}" if username else None)
        label = f"{html.escape(name)} " if name else ""
        lines.append(f"• {label}<code>{user_id}</code>")
    await message.reply("\n".join(lines))
