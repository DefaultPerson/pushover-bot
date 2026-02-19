"""Middleware to cancel FSM states when commands are received."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject


class FSMCancelMiddleware(BaseMiddleware):
    """Cancel FSM states when any command is received.

    This ensures that if a user is in the middle of an FSM flow and sends
    another command, the state is properly cancelled before the command runs.

    Must be registered as outer middleware to run before handlers.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Only process messages with text that look like commands
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            state: FSMContext | None = data.get("state")
            if state is not None:
                current_state = await state.get_state()
                if current_state is not None:
                    await state.clear()

        return await handler(event, data)
