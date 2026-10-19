from aiogram.filters import Filter
from aiogram.types import Message


class ViaThisBot(Filter):
    """Messages a user posted through this bot's inline mode."""

    async def __call__(self, message: Message) -> bool:
        return message.via_bot is not None and message.via_bot.id == message.bot.id
