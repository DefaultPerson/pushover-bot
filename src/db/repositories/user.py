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
    async def upsert(user_id: int, username: str | None = None, language: str = "ru") -> User:
        row = await db.fetchrow(
            """
            INSERT INTO users (id, username, language) VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE SET username = COALESCE($2, users.username), updated_at = NOW()
            RETURNING *
            """,
            user_id,
            username,
            language,
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
        return lang or "ru"
