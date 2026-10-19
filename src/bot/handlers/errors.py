import traceback

import structlog
from aiogram.types import ErrorEvent, Update

from src.config import settings
from src.db.repositories import GroupRepository, UserRepository
from src.i18n import get_text

log = structlog.get_logger()


async def _language(update: Update) -> str:
    callback = update.callback_query
    message = update.message or (callback.message if callback else None)
    user = (
        update.message.from_user if update.message else (callback.from_user if callback else None)
    )
    if message and message.chat.type in ("group", "supergroup"):
        return await GroupRepository.get_language(message.chat.id)
    if user:
        return await UserRepository.get_language(user.id)
    return settings.default_language


async def on_error(event: ErrorEvent) -> None:
    """Log any unhandled error and tell the user instead of staying silent."""
    update = event.update
    log.error(
        "Unhandled error",
        update_id=update.update_id,
        error=repr(event.exception),
        traceback="".join(traceback.format_exception(event.exception)),
    )

    try:
        text = get_text("error_generic", await _language(update))
        if update.message:
            await update.message.reply(text)
        elif update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
    except Exception as e:
        log.warning("Failed to report error to user", error=repr(e))
