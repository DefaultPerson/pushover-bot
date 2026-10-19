from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, TelegramObject, User

from src.bot.commands import refresh_chat_menu
from src.db.repositories import GroupRepository, UserRepository

log = structlog.get_logger()


class UserMiddleware(BaseMiddleware):
    """Auto-register users and groups on each message."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user:
            # Upsert user (always update username from Telegram)
            db_user = await UserRepository.upsert(
                user.id, username=user.username, full_name=user.full_name
            )
            data["db_user"] = db_user

        # Upsert group if message is from group
        if isinstance(event, Message) and event.chat.type in ("group", "supergroup"):
            group = await GroupRepository.upsert(event.chat.id, event.chat.title)
            # A new row means a group the startup menu refresh never saw,
            # and its menu may be pinned from before
            if group.created_at == group.updated_at:
                try:
                    await refresh_chat_menu(event.bot, event.chat.id, group.language, True)
                except TelegramAPIError as e:
                    log.warning("Group menu refresh failed", group_id=event.chat.id, error=str(e))

        return await handler(event, data)
