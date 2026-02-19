import structlog
from aiogram import Router
from aiogram.filters import JOIN_TRANSITION, KICKED, LEFT, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from src.db.repositories import GroupRepository

log = structlog.get_logger()

router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_bot_added(event: ChatMemberUpdated) -> None:
    """Handle bot being added to group."""
    if event.chat.type in ("group", "supergroup"):
        await GroupRepository.upsert(event.chat.id, event.chat.title)
        log.info("Bot added to group", group_id=event.chat.id, title=event.chat.title)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def on_bot_removed(event: ChatMemberUpdated) -> None:
    """Handle bot being removed from group."""
    await GroupRepository.set_bot_active(event.chat.id, False)
