from datetime import datetime, time

from src.config import settings
from src.db.database import db
from src.db.models import User


class UserRepository:
    @staticmethod
    async def get(user_id: int) -> User | None:
        row = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if row:
            return User(**dict(row))
        return None

    @staticmethod
    async def upsert(
        user_id: int,
        username: str | None = None,
        language: str | None = None,
        full_name: str | None = None,
    ) -> User:
        language = language or settings.default_language
        row = await db.fetchrow(
            """
            INSERT INTO users (id, username, language, full_name) VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                username = COALESCE($2, users.username),
                full_name = COALESCE($4, users.full_name),
                updated_at = NOW()
            RETURNING *
            """,
            user_id,
            username,
            language,
            full_name,
        )
        return User(**dict(row))

    @staticmethod
    async def get_by_username(username: str) -> User | None:
        row = await db.fetchrow(
            "SELECT * FROM users WHERE LOWER(username) = LOWER($1)",
            username,
        )
        if row:
            return User(**dict(row))
        return None

    @staticmethod
    async def set_pushover_key(user_id: int, key: str) -> None:
        await db.execute(
            """
            UPDATE users SET pushover_key = $1, updated_at = NOW()
            WHERE id = $2
            """,
            key,
            user_id,
        )

    @staticmethod
    async def set_language(user_id: int, language: str) -> None:
        await db.execute(
            """
            UPDATE users SET language = $1, updated_at = NOW()
            WHERE id = $2
            """,
            language,
            user_id,
        )

    @staticmethod
    async def get_language(user_id: int) -> str:
        lang = await db.fetchval("SELECT language FROM users WHERE id = $1", user_id)
        return lang or settings.default_language

    @staticmethod
    async def set_personal_gms(user_id: int, enabled: bool) -> None:
        await db.execute(
            "UPDATE users SET personal_gms = $2, updated_at = NOW() WHERE id = $1",
            user_id,
            enabled,
        )

    @staticmethod
    async def set_quiet_daily(user_id: int, start: time, end: time, tz: str) -> None:
        await db.execute(
            """
            UPDATE users SET quiet_start = $2, quiet_end = $3, quiet_tz = $4, updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
            start,
            end,
            tz,
        )

    @staticmethod
    async def set_quiet_period(
        user_id: int, quiet_from: datetime, quiet_to: datetime, tz: str | None = None
    ) -> None:
        """Set a one-off quiet period. A given tz also becomes the user's saved tz."""
        await db.execute(
            """
            UPDATE users SET quiet_from = $2, quiet_to = $3,
                quiet_tz = COALESCE($4, quiet_tz), updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
            quiet_from,
            quiet_to,
            tz,
        )

    @staticmethod
    async def clear_quiet(user_id: int) -> None:
        await db.execute(
            """
            UPDATE users SET quiet_start = NULL, quiet_end = NULL,
                quiet_from = NULL, quiet_to = NULL, updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
        )
