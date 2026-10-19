from src.db.database import db


class BlockRepository:
    @staticmethod
    async def add(blocker_id: int, blocked_id: int) -> None:
        await db.execute(
            """
            INSERT INTO user_blocks (blocker_id, blocked_id) VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            blocker_id,
            blocked_id,
        )

    @staticmethod
    async def remove(blocker_id: int, blocked_id: int) -> bool:
        """Returns True if a block was removed."""
        status = await db.execute(
            "DELETE FROM user_blocks WHERE blocker_id = $1 AND blocked_id = $2",
            blocker_id,
            blocked_id,
        )
        return status != "DELETE 0"

    @staticmethod
    async def get_blocked(blocker_id: int) -> list[tuple[int, str | None, str | None]]:
        """Blocked users as (id, full_name, username); names are None if the bot never saw them."""
        rows = await db.fetch(
            """
            SELECT b.blocked_id, u.full_name, u.username
            FROM user_blocks b
            LEFT JOIN users u ON u.id = b.blocked_id
            WHERE b.blocker_id = $1
            ORDER BY b.created_at
            """,
            blocker_id,
        )
        return [(row["blocked_id"], row["full_name"], row["username"]) for row in rows]
