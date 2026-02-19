import asyncio
import logging
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from aiogram_broadcast import (
    BroadcastMiddleware,
    BroadcastScheduler,
    BroadcastService,
    RedisBroadcastStorage,
)
from aiogram_broadcast.ui import BroadcastUIHandlers, BroadcastUIMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from src.bot.commands import ADMIN_COMMANDS, GROUP_COMMANDS, PRIVATE_COMMANDS
from src.bot.handlers import setup_routers
from src.bot.middlewares import (
    ArchiveMiddleware,
    FSMCancelMiddleware,
    I18nMiddleware,
    ThrottlingMiddleware,
    UserMiddleware,
)
from src.config import settings
from src.db.database import db
from src.i18n import load_locales
from src.services.broadcast import set_broadcast_service


async def setup_bot_commands(bot: Bot) -> None:
    """Set bot commands for menu in all supported languages."""
    # Set default commands (English) without language code
    await bot.set_my_commands(PRIVATE_COMMANDS["en"], scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(GROUP_COMMANDS["en"], scope=BotCommandScopeAllGroupChats())

    # Set language-specific commands
    for lang_code in ["ru", "uk"]:
        await bot.set_my_commands(
            PRIVATE_COMMANDS[lang_code],
            scope=BotCommandScopeAllPrivateChats(),
            language_code=lang_code,
        )
        await bot.set_my_commands(
            GROUP_COMMANDS[lang_code],
            scope=BotCommandScopeAllGroupChats(),
            language_code=lang_code,
        )

    # Set admin commands (private commands + admin commands) for each admin
    for admin_id in settings.admin_ids_list:
        await bot.set_my_commands(
            PRIVATE_COMMANDS["en"] + ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=admin_id),
        )


def setup_logging() -> None:
    """Configure structlog for JSON logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if settings.log_level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def main() -> None:
    setup_logging()
    log = structlog.get_logger()

    # Load i18n
    load_locales()

    # Connect to database (create if missing, apply migrations)
    await db.ensure_database()
    await db.connect()
    await db.run_migrations()

    # Connect to Redis
    redis = Redis.from_url(settings.redis_url)
    log.info(
        "Redis connected", url=settings.redis_url.replace(settings.redis_password or "", "***")
    )

    # Initialize FSM storage with Redis
    fsm_storage = RedisStorage(redis=redis)

    # Initialize broadcast storage with Redis
    broadcast_storage = RedisBroadcastStorage(redis=redis, key_prefix="broadcast")

    # Initialize bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Initialize broadcast service
    broadcast_svc = BroadcastService(bot=bot, storage=broadcast_storage)
    set_broadcast_service(broadcast_svc)

    # Initialize APScheduler for scheduled broadcasts
    apscheduler = AsyncIOScheduler()

    # Initialize broadcast scheduler
    broadcast_scheduler = BroadcastScheduler(
        service=broadcast_svc,
        scheduler=apscheduler,
    )

    # Initialize dispatcher with Redis FSM storage
    dp = Dispatcher(storage=fsm_storage)

    # Setup middlewares (order matters: broadcast first to track users, then fsm_cancel, i18n, user, throttling)
    broadcast_middleware = BroadcastMiddleware(broadcast_storage)
    dp.update.outer_middleware.register(broadcast_middleware)

    # Broadcast UI middleware (inner middleware for UI manager)
    dp.update.middleware.register(
        BroadcastUIMiddleware(
            service=broadcast_svc,
            scheduler=broadcast_scheduler,
        )
    )

    dp.message.outer_middleware.register(
        FSMCancelMiddleware()
    )  # Cancel FSM states on commands first
    dp.message.outer_middleware.register(ArchiveMiddleware())  # Archive group messages (if enabled)
    dp.message.middleware(I18nMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Setup routers
    dp.include_router(setup_routers())

    # Register broadcast UI handlers
    BroadcastUIHandlers().register(dp)

    # Setup bot commands menu
    await setup_bot_commands(bot)

    log.info("Bot starting...", bot_id=bot.id if hasattr(bot, "id") else "unknown")

    # Start APScheduler
    apscheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        apscheduler.shutdown()
        await db.disconnect()
        await redis.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
