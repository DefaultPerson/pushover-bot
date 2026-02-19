from src.db.database import db
from src.db.models import Subscription


class SubscriptionRepository:
    @staticmethod
    async def enable(user_id: int, group_id: int) -> None:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, group_id, enabled)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (user_id, group_id) DO UPDATE SET enabled = TRUE
            """,
            user_id,
            group_id,
        )

    @staticmethod
    async def disable(user_id: int, group_id: int) -> None:
        await db.execute(
            """
            UPDATE subscriptions SET enabled = FALSE
            WHERE user_id = $1 AND group_id = $2
            """,
            user_id,
            group_id,
        )

    @staticmethod
    async def is_enabled(user_id: int, group_id: int) -> bool:
        val = await db.fetchval(
            """
            SELECT enabled FROM subscriptions
            WHERE user_id = $1 AND group_id = $2
            """,
            user_id,
            group_id,
        )
        return val or False

    @staticmethod
    async def get_enabled_users_in_group(group_id: int) -> list[int]:
        """Get all user IDs with enabled notifications in the group."""
        rows = await db.fetch(
            """
            SELECT u.id, u.pushover_key
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.group_id = $1 AND s.enabled = TRUE AND u.pushover_key IS NOT NULL
            """,
            group_id,
        )
        return [row["id"] for row in rows]

    @staticmethod
    async def get_user_with_key(user_id: int) -> tuple[int, str] | None:
        """Get user with pushover key if exists."""
        row = await db.fetchrow(
            "SELECT id, pushover_key FROM users WHERE id = $1 AND pushover_key IS NOT NULL",
            user_id,
        )
        if row:
            return row["id"], row["pushover_key"]
        return None

    @staticmethod
    async def get_enabled_users_with_keys(group_id: int) -> list[tuple[int, str]]:
        """Get all (user_id, pushover_key) pairs for enabled users in group."""
        rows = await db.fetch(
            """
            SELECT u.id, u.pushover_key
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.group_id = $1 AND s.enabled = TRUE AND u.pushover_key IS NOT NULL
            """,
            group_id,
        )
        return [(row["id"], row["pushover_key"]) for row in rows]

    @staticmethod
    async def get_user_groups(user_id: int) -> list[tuple[int, str | None, bool]]:
        """Get all groups where user has enabled notifications.

        Returns (group_id, title, bot_active).
        """
        rows = await db.fetch(
            """
            SELECT g.id, g.title, g.bot_active
            FROM subscriptions s
            JOIN groups g ON s.group_id = g.id
            WHERE s.user_id = $1 AND s.enabled = TRUE
            """,
            user_id,
        )
        return [(row["id"], row["title"], row["bot_active"]) for row in rows]

    @staticmethod
    async def get_active_subscription_count(user_id: int) -> int:
        """Count groups where user has enabled subscriptions."""
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM subscriptions
            WHERE user_id = $1 AND enabled = TRUE
            """,
            user_id,
        )
        return count or 0

    @staticmethod
    async def get_enabled_user_by_username(
        username: str, group_id: int
    ) -> tuple[int, str] | None:
        """Find user by username among enabled subscribers of a group with a Pushover key."""
        row = await db.fetchrow(
            """
            SELECT u.id, u.pushover_key
            FROM users u
            JOIN subscriptions s ON u.id = s.user_id
            WHERE LOWER(u.username) = LOWER($1)
              AND s.group_id = $2
              AND s.enabled = TRUE
              AND u.pushover_key IS NOT NULL
            """,
            username,
            group_id,
        )
        if row:
            return row["id"], row["pushover_key"]
        return None
