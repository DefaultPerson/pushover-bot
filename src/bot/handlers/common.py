from collections.abc import Callable

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.bot.filters import IsGroup, IsPrivate
from src.db.models import User
from src.services.notification import notification_service

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


@router.message(Command("gm"), IsPrivate())
async def cmd_gm_private(message: Message, _: Callable) -> None:
    await message.answer(_("only_group"))
