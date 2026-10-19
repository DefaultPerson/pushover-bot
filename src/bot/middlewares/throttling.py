from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.config import settings
from src.db.repositories import NotificationLogRepository


class ThrottlingMiddleware(BaseMiddleware):
    """Rate limiting for /gm, /pgm, inline alerts and /test_alarm."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Forwarded commands are ignored by the handlers, so they cost nothing
        if not isinstance(event, Message) or not event.text or event.forward_origin:
            return await handler(event, data)

        text = event.text.lower()

        # Check /gm, /pgm and inline alert rate limit in groups
        via_this_bot = event.via_bot is not None and event.via_bot.id == event.bot.id
        is_gm = text.startswith(("/gm", "/pgm")) or via_this_bot
        if is_gm and event.chat.type in ("group", "supergroup"):
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
