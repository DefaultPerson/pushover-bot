from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.config import settings
from src.db.repositories import NotificationLogRepository


class ThrottlingMiddleware(BaseMiddleware):
    """Rate limiting for /gm and /test_alarm commands."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        text = event.text.lower()

        # Check /gm rate limit in groups
        if text.startswith("/gm") and event.chat.type in ("group", "supergroup"):
            allowed = await NotificationLogRepository.check_gm_rate_limit(
                group_id=event.chat.id,
                window_seconds=settings.gm_rate_window,
                max_calls=settings.gm_rate_limit,
            )
            if not allowed:
                _ = data.get("_", lambda k, **kw: k)
                await event.reply(_("rate_limit_gm"))
                return None

        # Check /test_alarm rate limit
        if text.startswith("/test_alarm") and event.from_user:
            allowed = await NotificationLogRepository.check_test_alarm_rate_limit(
                user_id=event.from_user.id,
                window_seconds=settings.test_alarm_rate_window,
                max_calls=settings.test_alarm_rate_limit,
            )
            if not allowed:
                _ = data.get("_", lambda k, **kw: k)
                await event.reply(_("rate_limit_test"))
                return None

        return await handler(event, data)
