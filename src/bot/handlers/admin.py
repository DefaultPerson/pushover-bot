"""Admin handlers for broadcast functionality."""

from typing import TYPE_CHECKING

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.filters import IsPrivate
from src.config import settings
from src.services.broadcast import get_broadcast_service

if TYPE_CHECKING:
    from aiogram_broadcast.storage import BaseBroadcastStorage
    from aiogram_broadcast.ui import BroadcastUIManager

router = Router()
router.message.filter(IsPrivate())

log = structlog.get_logger()


def is_admin(user_id: int) -> bool:
    """Check if user is in admin list."""
    return user_id in settings.admin_ids_list


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    broadcast_ui: BroadcastUIManager,
    broadcast_storage: BaseBroadcastStorage,
) -> None:
    """Start interactive broadcast UI (admin only)."""
    if not is_admin(message.from_user.id):
        return

    if broadcast_ui is None:
        await message.answer("Broadcast UI not initialized.")
        return

    # Get all active subscriber IDs
    subscriber_ids = await broadcast_storage.get_all_subscriber_ids()

    # Open the broadcast UI menu (pass None for callback - UI handles return internally)
    await broadcast_ui.open_menu(subscriber_ids)
    await message.delete()


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show bot statistics (admin only)."""
    if not is_admin(message.from_user.id):
        return

    broadcast_service = get_broadcast_service()
    if broadcast_service is None:
        await message.answer("Broadcast service not initialized.")
        return

    total = await broadcast_service.get_subscriber_count(only_active=False)
    active = await broadcast_service.get_subscriber_count(only_active=True)

    await message.answer(
        f"<b>Bot Statistics</b>\n\n"
        f"Total subscribers: {total}\n"
        f"Active subscribers: {active}\n"
        f"Blocked/kicked: {total - active}"
    )
