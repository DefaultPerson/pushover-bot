from src.db.database import db
from src.db.models import User


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
    async def get_recipients(
        group_id: int, sender_id: int, user_id: int | None = None
    ) -> list[User]:
        """Enabled users with a key in the group, minus those who blocked the sender.

        With user_id, returns only that user (or nothing).
        """
        rows = await db.fetch(
            """
            SELECT u.*
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.group_id = $1 AND s.enabled = TRUE AND u.pushover_key IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM user_blocks b WHERE b.blocker_id = u.id AND b.blocked_id = $2
              )
              AND ($3::BIGINT IS NULL OR u.id = $3)
            """,
            group_id,
            sender_id,
            user_id,
        )
        return [User(**dict(row)) for row in rows]

    @staticmethod
    async def get_inline_candidates(sender_id: int) -> list[User]:
        """People the sender can alert personally, from all groups shared with the sender."""
        rows = await db.fetch(
            """
            SELECT DISTINCT u.*
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.enabled = TRUE AND u.pushover_key IS NOT NULL
              AND u.personal_gms = TRUE AND u.id <> $1
              AND s.group_id IN (
                  SELECT group_id FROM subscriptions WHERE user_id = $1
                  UNION
                  SELECT group_id FROM gm_history WHERE user_id = $1
              )
              AND NOT EXISTS (
                  SELECT 1 FROM user_blocks b WHERE b.blocker_id = u.id AND b.blocked_id = $1
              )
            ORDER BY u.full_name NULLS LAST, u.username NULLS LAST
            """,
            sender_id,
        )
        return [User(**dict(row)) for row in rows]

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
    async def get_enabled_user_by_username(username: str, group_id: int) -> tuple[int, str] | None:
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
