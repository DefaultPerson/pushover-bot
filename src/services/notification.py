from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import structlog

from src.db.models import User
from src.db.repositories import (
    NotificationLogRepository,
    SubscriptionRepository,
    UserRepository,
)
from src.i18n import get_text
from src.services.pushover import pushover_client
from src.services.quiet import is_quiet

log = structlog.get_logger()


@dataclass
class GmResult:
    success: int = 0
    fail: int = 0
    # Recipients who got the alert silently because of their quiet hours
    quiet_names: list[str] = field(default_factory=list)
    # Pushover tag for cancel_by_tag; None if no alert with retries went out
    tag: str | None = None
    # Last Pushover error
    error: str | None = None
    # Locale key when a personal alert was refused before sending
    refusal: str | None = None


class NotificationService:
    @staticmethod
    async def _deliver(
        recipients: list[User],
        group_id: int,
        sender_id: int,
        sender_name: str,
        message: str | None,
        notification_type: str,
    ) -> GmResult:
        result = GmResult()
        tag = f"gm{uuid4().hex[:16]}"
        now = datetime.now(UTC)

        for user in recipients:
            # Quiet hours mute alerts from others, never your own
            quiet = user.id != sender_id and is_quiet(user, now)
            ok, error = await pushover_client.send_emergency(
                user.pushover_key,
                message or get_text("push_default", user.language, sender=sender_name),
                title=get_text("push_title", user.language),
                priority=-1 if quiet else 2,
                tags=None if quiet else tag,
            )

            await NotificationLogRepository.log(
                sender_id=sender_id,
                recipient_id=user.id,
                notification_type=notification_type,
                pushover_success=ok,
                group_id=group_id,
                error_message=error,
            )

            if not ok:
                result.fail += 1
                result.error = error
                continue
            result.success += 1
            if quiet:
                result.quiet_names.append(user.display_name)
            else:
                result.tag = tag

        await NotificationLogRepository.record_gm_call(group_id, sender_id)
        return result

    @staticmethod
    async def send_gm_to_all(
        group_id: int,
        sender_id: int,
        sender_name: str,
        message: str | None = None,
    ) -> GmResult:
        """Send emergency notification to all enabled users in group."""
        users = await SubscriptionRepository.get_recipients(group_id, sender_id)
        result = await NotificationService._deliver(
            users, group_id, sender_id, sender_name, message, "gm"
        )

        log.info(
            "GM sent",
            group_id=group_id,
            sender_id=sender_id,
            success=result.success,
            fail=result.fail,
            quiet=len(result.quiet_names),
        )

        return result

    @staticmethod
    async def send_gm_to_user(
        group_id: int,
        sender_id: int,
        target_user_id: int,
        sender_name: str,
        message: str | None = None,
    ) -> GmResult:
        """Send emergency notification to specific user."""
        # Empty if the target is not subscribed here, has no key or blocked the sender
        users = await SubscriptionRepository.get_recipients(group_id, sender_id, target_user_id)
        if not users:
            return GmResult(refusal="gm_user_not_found")
        if not users[0].personal_gms and target_user_id != sender_id:
            return GmResult(refusal="pgm_personal_off")

        return await NotificationService._deliver(
            users, group_id, sender_id, sender_name, message, "gm_single"
        )

    @staticmethod
    async def send_test_alarm(user_id: int) -> tuple[bool, str | None]:
        """
        Send test alarm to self.
        Returns: (success, error_message)
        """
        user = await UserRepository.get(user_id)

        if not user or not user.pushover_key:
            return False, "No Pushover key configured"

        ok, error = await pushover_client.send_emergency(
            user.pushover_key,
            get_text("push_test", user.language),
            title=get_text("push_test_title", user.language),
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
