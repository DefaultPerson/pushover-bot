"""Middleware to archive all group messages to database."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject

from src.config import settings
from src.db.database import db

log = structlog.get_logger()


class ArchiveMiddleware(BaseMiddleware):
    """Archive all group messages to database and save media to disk."""

    def __init__(self):
        self.media_path = Path(settings.archive_media_path)
        if settings.archive_enabled:
            self.media_path.mkdir(parents=True, exist_ok=True)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Only process if archiving is enabled and it's a group message
        if (
            settings.archive_enabled
            and isinstance(event, Message)
            and event.chat.type in ("group", "supergroup")
        ):
            try:
                await self._archive_message(event, data.get("bot"))
            except Exception as e:
                log.error("Failed to archive message", error=str(e), message_id=event.message_id)

        return await handler(event, data)

    async def _archive_message(self, message: Message, bot: Bot | None) -> None:
        """Archive a single message."""
        # Extract user info
        user = message.from_user
        user_id = user.id if user else None
        username = user.username if user else None
        first_name = user.first_name if user else None
        last_name = user.last_name if user else None

        # Extract media info
        media_type = None
        media_file_id = None
        media_file_path = None
        media_file_name = None
        media_mime_type = None
        media_file_size = None

        # Check for different media types
        if message.photo:
            media_type = "photo"
            # Get largest photo
            photo = message.photo[-1]
            media_file_id = photo.file_id
            media_file_size = photo.file_size
        elif message.video:
            media_type = "video"
            media_file_id = message.video.file_id
            media_file_name = message.video.file_name
            media_mime_type = message.video.mime_type
            media_file_size = message.video.file_size
        elif message.document:
            media_type = "document"
            media_file_id = message.document.file_id
            media_file_name = message.document.file_name
            media_mime_type = message.document.mime_type
            media_file_size = message.document.file_size
        elif message.audio:
            media_type = "audio"
            media_file_id = message.audio.file_id
            media_file_name = message.audio.file_name
            media_mime_type = message.audio.mime_type
            media_file_size = message.audio.file_size
        elif message.voice:
            media_type = "voice"
            media_file_id = message.voice.file_id
            media_mime_type = message.voice.mime_type
            media_file_size = message.voice.file_size
        elif message.video_note:
            media_type = "video_note"
            media_file_id = message.video_note.file_id
            media_file_size = message.video_note.file_size
        elif message.sticker:
            media_type = "sticker"
            media_file_id = message.sticker.file_id
            media_file_size = message.sticker.file_size
        elif message.animation:
            media_type = "animation"
            media_file_id = message.animation.file_id
            media_file_name = message.animation.file_name
            media_mime_type = message.animation.mime_type
            media_file_size = message.animation.file_size

        # Download media if present
        if media_file_id and bot:
            try:
                media_file_path = await self._download_media(
                    bot, message.chat.id, message.message_id, media_file_id, media_type, media_file_name
                )
            except Exception as e:
                log.warning("Failed to download media", error=str(e), file_id=media_file_id)

        # Extract forward info
        forward_from_user_id = None
        forward_from_chat_id = None
        forward_date = None

        if message.forward_origin:
            if hasattr(message.forward_origin, 'sender_user') and message.forward_origin.sender_user:
                forward_from_user_id = message.forward_origin.sender_user.id
            if hasattr(message.forward_origin, 'chat') and message.forward_origin.chat:
                forward_from_chat_id = message.forward_origin.chat.id
            if hasattr(message.forward_origin, 'date'):
                forward_date = message.forward_origin.date

        # Insert into database
        await db.execute(
            """
            INSERT INTO archived_messages (
                message_id, group_id, user_id, username, first_name, last_name,
                text, caption, media_type, media_file_id, media_file_path,
                media_file_name, media_mime_type, media_file_size,
                reply_to_message_id, forward_from_user_id, forward_from_chat_id,
                forward_date, message_date
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
            )
            ON CONFLICT (group_id, message_id) DO NOTHING
            """,
            message.message_id,
            message.chat.id,
            user_id,
            username,
            first_name,
            last_name,
            message.text,
            message.caption,
            media_type,
            media_file_id,
            media_file_path,
            media_file_name,
            media_mime_type,
            media_file_size,
            message.reply_to_message.message_id if message.reply_to_message else None,
            forward_from_user_id,
            forward_from_chat_id,
            forward_date,
            message.date,
        )

    async def _download_media(
        self,
        bot: Bot,
        group_id: int,
        message_id: int,
        file_id: str,
        media_type: str,
        original_name: str | None,
    ) -> str:
        """Download media file and return local path."""
        # Create group subfolder
        group_folder = self.media_path / str(group_id)
        group_folder.mkdir(parents=True, exist_ok=True)

        # Get file info from Telegram
        file = await bot.get_file(file_id)

        # Determine extension
        if original_name:
            ext = Path(original_name).suffix or self._get_extension(media_type, file.file_path)
        else:
            ext = self._get_extension(media_type, file.file_path)

        # Generate filename: message_id_type.ext
        filename = f"{message_id}_{media_type}{ext}"
        local_path = group_folder / filename

        # Download file
        await bot.download_file(file.file_path, local_path)

        return str(local_path)

    def _get_extension(self, media_type: str, file_path: str | None) -> str:
        """Get file extension based on media type or file path."""
        if file_path:
            ext = Path(file_path).suffix
            if ext:
                return ext

        # Default extensions by media type
        defaults = {
            "photo": ".jpg",
            "video": ".mp4",
            "audio": ".mp3",
            "voice": ".ogg",
            "video_note": ".mp4",
            "sticker": ".webp",
            "animation": ".mp4",
            "document": "",
        }
        return defaults.get(media_type, "")
