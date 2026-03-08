import structlog
from aiogram import Router
from aiogram.filters import JOIN_TRANSITION, KICKED, LEFT, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from src.db.repositories import GroupRepository, SubscriptionRepository

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


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def on_user_left(event: ChatMemberUpdated) -> None:
    """Disable subscription when a user leaves or is kicked from a group."""
    user_id = event.new_chat_member.user.id
    group_id = event.chat.id
    await SubscriptionRepository.disable(user_id, group_id)
    log.info("User left group, subscription disabled", user_id=user_id, group_id=group_id)
