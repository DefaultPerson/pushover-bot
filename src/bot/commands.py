"""Bot command definitions for localized menus."""

import asyncio

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import BotCommand, BotCommandScopeChat
from redis.asyncio import Redis

from src.config import settings

log = structlog.get_logger()

# Bump when the lists below change, so per-chat menus get refreshed on startup
MENU_VERSION = "2"
MENU_VERSION_KEY = "menu_version"

# Private chat commands per language
PRIVATE_COMMANDS = {
    "en": [
        BotCommand(command="start", description="Start / Show info"),
        BotCommand(command="key", description="Configure Pushover key"),
        BotCommand(command="list", description="List groups with notifications"),
        BotCommand(command="test_alarm", description="Send test alarm"),
        BotCommand(command="quiet", description="Quiet hours"),
        BotCommand(command="blocks", description="People you blocked"),
        BotCommand(command="personalgms", description="Allow or refuse personal alerts"),
        BotCommand(command="language", description="Change language"),
        BotCommand(command="id", description="Your id"),
        BotCommand(command="help", description="Show help"),
    ],
    "ru": [
        BotCommand(command="start", description="Начать / Показать информацию"),
        BotCommand(command="key", description="Настроить Pushover ключ"),
        BotCommand(command="list", description="Список групп с уведомлениями"),
        BotCommand(command="test_alarm", description="Тестовая сирена"),
        BotCommand(command="quiet", description="Тихие часы"),
        BotCommand(command="blocks", description="Кого вы заблокировали"),
        BotCommand(command="personalgms", description="Принимать ли личные алерты"),
        BotCommand(command="language", description="Сменить язык"),
        BotCommand(command="id", description="Ваш id"),
        BotCommand(command="help", description="Справка"),
    ],
    "uk": [
        BotCommand(command="start", description="Почати / Показати інформацію"),
        BotCommand(command="key", description="Налаштувати Pushover ключ"),
        BotCommand(command="list", description="Список груп зі сповіщеннями"),
        BotCommand(command="test_alarm", description="Тестова сирена"),
        BotCommand(command="quiet", description="Тихі години"),
        BotCommand(command="blocks", description="Кого ви заблокували"),
        BotCommand(command="personalgms", description="Чи приймати особисті алерти"),
        BotCommand(command="language", description="Змінити мову"),
        BotCommand(command="id", description="Ваш id"),
        BotCommand(command="help", description="Допомога"),
    ],
}

# Group chat commands per language
GROUP_COMMANDS = {
    "en": [
        BotCommand(command="gm", description="Wake up everyone"),
        BotCommand(command="pgm", description="Wake up one person"),
        BotCommand(command="enable", description="Enable notifications"),
        BotCommand(command="disable", description="Disable notifications"),
        BotCommand(command="test_alarm", description="Send test alarm to yourself"),
        BotCommand(command="quiet", description="Quiet hours"),
        BotCommand(command="block", description="Block alerts from a person (reply)"),
        BotCommand(command="id", description="Ids of you, chat and topic"),
        BotCommand(command="only_admin", description="Only admins can use /gm"),
        BotCommand(command="confirm_gm", description="Ask before waking everyone"),
        BotCommand(command="language", description="Change group language"),
        BotCommand(command="help", description="Show help"),
    ],
    "ru": [
        BotCommand(command="gm", description="Разбудить всех"),
        BotCommand(command="pgm", description="Разбудить одного"),
        BotCommand(command="enable", description="Включить уведомления"),
        BotCommand(command="disable", description="Выключить уведомления"),
        BotCommand(command="test_alarm", description="Тестовая сирена себе"),
        BotCommand(command="quiet", description="Тихие часы"),
        BotCommand(command="block", description="Блокировать алерты человека (ответом)"),
        BotCommand(command="id", description="id ваш, чата и топика"),
        BotCommand(command="only_admin", description="Только админы могут /gm"),
        BotCommand(command="confirm_gm", description="Спрашивать перед «разбудить всех»"),
        BotCommand(command="language", description="Изменить язык группы"),
        BotCommand(command="help", description="Справка"),
    ],
    "uk": [
        BotCommand(command="gm", description="Розбудити всіх"),
        BotCommand(command="pgm", description="Розбудити одного"),
        BotCommand(command="enable", description="Увімкнути сповіщення"),
        BotCommand(command="disable", description="Вимкнути сповіщення"),
        BotCommand(command="test_alarm", description="Тестова сирена собі"),
        BotCommand(command="quiet", description="Тихі години"),
        BotCommand(command="block", description="Блокувати алерти людини (відповіддю)"),
        BotCommand(command="id", description="id ваш, чату й топіка"),
        BotCommand(command="only_admin", description="Тільки адміни можуть /gm"),
        BotCommand(command="confirm_gm", description="Питати перед «розбудити всіх»"),
        BotCommand(command="language", description="Змінити мову групи"),
        BotCommand(command="help", description="Допомога"),
    ],
}

# Admin commands (appended to private commands for admins)
ADMIN_COMMANDS = [
    BotCommand(command="broadcast", description="Send broadcast to all users"),
    BotCommand(command="stats", description="Show bot statistics"),
]


async def apply_user_menu(bot: Bot, user_id: int, lang: str) -> None:
    """Pin the private menu of one user to the language chosen in /language."""
    commands = PRIVATE_COMMANDS.get(lang, PRIVATE_COMMANDS["en"])
    if user_id in settings.admin_ids_list:
        commands = commands + ADMIN_COMMANDS
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))


async def apply_group_menu(bot: Bot, chat_id: int, lang: str) -> None:
    """Pin the menu of one group to the language chosen in /language."""
    commands = GROUP_COMMANDS.get(lang, GROUP_COMMANDS["en"])
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))


async def refresh_chat_menus(bot: Bot, redis: Redis, chats: list[tuple[int, str, bool]]) -> None:
    """Re-apply per-chat menus once per MENU_VERSION.

    /language pins a chat's menu, which then hides commands added later.
    Only chats that already have a pinned menu are touched.
    chats: (chat_id, language, is_group).
    """
    if await redis.get(MENU_VERSION_KEY) == MENU_VERSION.encode():
        return

    refreshed = 0
    for chat_id, lang, is_group in chats:
        for _attempt in range(2):
            try:
                if await bot.get_my_commands(scope=BotCommandScopeChat(chat_id=chat_id)):
                    if is_group:
                        await apply_group_menu(bot, chat_id, lang)
                    else:
                        await apply_user_menu(bot, chat_id, lang)
                    refreshed += 1
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except TelegramAPIError:
                break
        await asyncio.sleep(0.05)

    await redis.set(MENU_VERSION_KEY, MENU_VERSION)
    log.info("Chat menus refreshed", version=MENU_VERSION, checked=len(chats), refreshed=refreshed)
