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
    ) -> tuple[bool, str | None]:
        """
        Send emergency notification (priority=2).
        Bypasses quiet hours, plays siren sound, retries until acknowledged.

        Returns: (success, error_message)
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    self.BASE_URL,
                    data={
                        "token": self.app_token,
                        "user": user_key,
                        "message": message,
                        "title": title,
                        "priority": 2,
                        "retry": 30,
                        "expire": 3600,
                        "sound": "siren",
                    },
                )

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
