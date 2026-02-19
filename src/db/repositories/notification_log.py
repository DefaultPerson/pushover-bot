from src.db.database import db


class NotificationLogRepository:
    @staticmethod
    async def log(
        sender_id: int,
        recipient_id: int,
        notification_type: str,
        pushover_success: bool,
        group_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        await db.execute(
            """
            INSERT INTO notification_logs
            (group_id, sender_id, recipient_id, notification_type, pushover_success, error_message)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            group_id,
            sender_id,
            recipient_id,
            notification_type,
            pushover_success,
            error_message,
        )

    @staticmethod
    async def check_gm_rate_limit(group_id: int, window_seconds: int, max_calls: int) -> bool:
        """Check if /gm rate limit is exceeded. Returns True if allowed."""
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM gm_history
            WHERE group_id = $1 AND called_at > NOW() - INTERVAL '1 second' * $2
            """,
            group_id,
            window_seconds,
        )
        return count < max_calls

    @staticmethod
    async def record_gm_call(group_id: int, user_id: int) -> None:
        await db.execute(
            "INSERT INTO gm_history (group_id, user_id) VALUES ($1, $2)",
            group_id,
            user_id,
        )

    @staticmethod
    async def check_test_alarm_rate_limit(
        user_id: int, window_seconds: int, max_calls: int
    ) -> bool:
        """Check test_alarm rate limit per user. Returns True if allowed."""
        count = await db.fetchval(
            """
            SELECT COUNT(*) FROM notification_logs
            WHERE sender_id = $1
              AND notification_type = 'test_alarm'
              AND created_at > NOW() - INTERVAL '1 second' * $2
            """,
            user_id,
            window_seconds,
        )
        return count < max_calls
