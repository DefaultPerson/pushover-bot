from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from src.config import settings
from src.db.repositories import GroupRepository, UserRepository
from src.i18n import get_text


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        language = settings.default_language

        # Determine chat type from event
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        if chat:
            # Group chats: use group's language setting
            if chat.type in ("group", "supergroup"):
                language = await GroupRepository.get_language(chat.id)
            # Private chats: use user's language setting
            elif chat.type == "private" and user:
                language = await UserRepository.get_language(user.id)
        elif user:
            # Fallback to user language if no chat context
            language = await UserRepository.get_language(user.id)

        # Add i18n helper to data
        data["_"] = lambda key, **kwargs: get_text(key, language, **kwargs)
        data["lang"] = language

        return await handler(event, data)
