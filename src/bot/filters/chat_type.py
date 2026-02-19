from aiogram.filters import Filter
from aiogram.types import Message


class IsPrivate(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type == "private"


class IsGroup(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ("group", "supergroup")
