from src.db.database import db
from src.db.models import Group


class GroupRepository:
    @staticmethod
    async def get(group_id: int) -> Group | None:
        row = await db.fetchrow("SELECT * FROM groups WHERE id = $1", group_id)
        if row:
            return Group(**dict(row))
        return None

    @staticmethod
    async def upsert(group_id: int, title: str | None = None) -> Group:
        row = await db.fetchrow(
            """
            INSERT INTO groups (id, title) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET
                title = COALESCE($2, groups.title),
                bot_active = TRUE,
                updated_at = NOW()
            RETURNING *
            """,
            group_id,
            title,
        )
        return Group(**dict(row))

    @staticmethod
    async def toggle_only_admin(group_id: int) -> bool:
        """Toggle only_admin flag. Returns new value."""
        new_value = await db.fetchval(
            """
            UPDATE groups SET only_admin = NOT only_admin, updated_at = NOW()
            WHERE id = $1
            RETURNING only_admin
            """,
            group_id,
        )
        return new_value or False

    @staticmethod
    async def is_only_admin(group_id: int) -> bool:
        val = await db.fetchval("SELECT only_admin FROM groups WHERE id = $1", group_id)
        return val or False

    @staticmethod
    async def set_language(group_id: int, language: str) -> None:
        """Set the language for a group."""
        await db.execute(
            """
            INSERT INTO groups (id, language) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET language = $2, updated_at = NOW()
            """,
            group_id,
            language,
        )

    @staticmethod
    async def get_language(group_id: int) -> str:
        """Get the language for a group. Returns 'en' if not found."""
        val = await db.fetchval("SELECT language FROM groups WHERE id = $1", group_id)
        return val or "en"

    @staticmethod
    async def set_bot_active(group_id: int, active: bool) -> None:
        """Set the bot_active status for a group."""
        await db.execute(
            """
            UPDATE groups SET bot_active = $2, updated_at = NOW()
            WHERE id = $1
            """,
            group_id,
            active,
        )
