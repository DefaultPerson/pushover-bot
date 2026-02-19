import structlog

from src.db.repositories import (
    NotificationLogRepository,
    SubscriptionRepository,
    UserRepository,
)
from src.services.pushover import pushover_client

log = structlog.get_logger()


class NotificationService:
    @staticmethod
    async def send_gm_to_all(
        group_id: int,
        sender_id: int,
        sender_name: str,
        message: str | None = None,
    ) -> tuple[int, int]:
        """
        Send emergency notification to all enabled users in group.
        Returns: (success_count, fail_count)
        """
        if message is None:
            message = f"Wake up! {sender_name} is calling!"

        users = await SubscriptionRepository.get_enabled_users_with_keys(group_id)

        success = 0
        fail = 0

        for user_id, pushover_key in users:
            ok, error = await pushover_client.send_emergency(pushover_key, message)

            await NotificationLogRepository.log(
                sender_id=sender_id,
                recipient_id=user_id,
                notification_type="gm",
                pushover_success=ok,
                group_id=group_id,
                error_message=error,
            )

            if ok:
                success += 1
            else:
                fail += 1

        await NotificationLogRepository.record_gm_call(group_id, sender_id)

        log.info(
            "GM sent",
            group_id=group_id,
            sender_id=sender_id,
            success=success,
            fail=fail,
        )

        return success, fail

    @staticmethod
    async def send_gm_to_user(
        group_id: int,
        sender_id: int,
        target_user_id: int,
        sender_name: str,
        message: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Send emergency notification to specific user.
        Returns: (success, error_message)
        """
        if message is None:
            message = f"Wake up! {sender_name} is calling!"

        user = await UserRepository.get(target_user_id)

        if not user or not user.pushover_key:
            return False, "User not found or no Pushover key"

        # Check if user has enabled notifications in this group
        is_enabled = await SubscriptionRepository.is_enabled(target_user_id, group_id)
        if not is_enabled:
            return False, "User has not enabled notifications in this group"

        ok, error = await pushover_client.send_emergency(user.pushover_key, message)

        await NotificationLogRepository.log(
            sender_id=sender_id,
            recipient_id=target_user_id,
            notification_type="gm_single",
            pushover_success=ok,
            group_id=group_id,
            error_message=error,
        )

        await NotificationLogRepository.record_gm_call(group_id, sender_id)

        return ok, error

    @staticmethod
    async def send_test_alarm(
        user_id: int,
        message: str = "Test alarm! If you see this, Pushover is working.",
    ) -> tuple[bool, str | None]:
        """
        Send test alarm to self.
        Returns: (success, error_message)
        """
        user = await UserRepository.get(user_id)

        if not user or not user.pushover_key:
            return False, "No Pushover key configured"

        ok, error = await pushover_client.send_emergency(
            user.pushover_key,
            message,
            title="TEST ALARM",
        )

        await NotificationLogRepository.log(
            sender_id=user_id,
            recipient_id=user_id,
            notification_type="test_alarm",
            pushover_success=ok,
            group_id=None,
            error_message=error,
        )

        return ok, error


notification_service = NotificationService()
