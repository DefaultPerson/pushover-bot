import httpx
import structlog

from src.config import settings

log = structlog.get_logger()


class PushoverClient:
    BASE_URL = "https://api.pushover.net/1/messages.json"

    def __init__(self, app_token: str | None = None):
        self.app_token = app_token or settings.pushover_app_token

    async def send_emergency(
        self,
        user_key: str,
        message: str,
        title: str = "ALARM",
        priority: int = 2,
        tags: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Send emergency notification (priority=2).
        Bypasses quiet hours, plays siren sound, retries until acknowledged.
        priority=-1 delivers it silently, without retries.
        Retries of all messages sharing a tag can be stopped with cancel_by_tag().

        Returns: (success, error_message)
        """
        data = {
            "token": self.app_token,
            "user": user_key,
            "message": message,
            "title": title,
            "priority": priority,
        }
        if priority == 2:
            data |= {"retry": 30, "expire": 3600, "sound": "siren"}
            if tags:
                data["tags"] = tags

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(self.BASE_URL, data=data)

                if resp.status_code == 200:
                    log.info("Pushover sent", user_key=user_key[:8] + "...")
                    return True, None

                error = resp.text
                log.error("Pushover failed", status=resp.status_code, error=error)
                return False, error

            except httpx.TimeoutException:
                log.error("Pushover timeout", user_key=user_key[:8] + "...")
                return False, "Timeout"
            except Exception as e:
                log.error("Pushover error", error=str(e))
                return False, str(e)

    async def cancel_by_tag(self, tag: str) -> bool:
        """Stop retries of all emergency notifications sent with this tag."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"https://api.pushover.net/1/receipts/cancel_by_tag/{tag}.json",
                    data={"token": self.app_token},
                )
                if resp.status_code == 200:
                    return True
                log.error("Pushover cancel failed", status=resp.status_code, error=resp.text)
                return False
            except Exception as e:
                log.error("Pushover cancel error", error=str(e))
                return False

    async def validate_user_key(self, user_key: str) -> bool:
        """Validate Pushover user key."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    "https://api.pushover.net/1/users/validate.json",
                    data={
                        "token": self.app_token,
                        "user": user_key,
                    },
                )
                return resp.status_code == 200
            except Exception:
                return False


pushover_client = PushoverClient()
