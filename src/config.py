from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str

    # Pushover
    pushover_app_token: str

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "pushover"
    db_user: str = "bot"
    db_password: str

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # Admin IDs (comma-separated list of Telegram user IDs who can broadcast)
    admin_ids: str = ""

    # Logging
    log_level: str = "INFO"

    # Rate limits
    gm_rate_limit: int = 3  # max calls
    gm_rate_window: int = 300  # seconds (5 min)
    test_alarm_rate_limit: int = 1
    test_alarm_rate_window: int = 60  # 1 min

    # Archive settings
    archive_enabled: bool = False
    archive_media_path: str = "archive/media"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def admin_ids_list(self) -> list[int]:
        """Parse comma-separated admin IDs into list of integers."""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()]


settings = Settings()
