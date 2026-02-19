from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User

from src.db.repositories import GroupRepository, UserRepository


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
            db_user = await UserRepository.upsert(user.id, username=user.username)
            data["db_user"] = db_user

        # Upsert group if message is from group
        if isinstance(event, Message) and event.chat.type in ("group", "supergroup"):
            await GroupRepository.upsert(event.chat.id, event.chat.title)

        return await handler(event, data)
