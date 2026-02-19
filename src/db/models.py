from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    username: str | None = None
    pushover_key: str | None = None
    language: str = "en"
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Group:
    id: int
    title: str | None = None
    only_admin: bool = False
    language: str = "en"
    bot_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Subscription:
    user_id: int
    group_id: int
    enabled: bool = True
    created_at: datetime | None = None


@dataclass
class NotificationLog:
    id: int | None = None
    group_id: int | None = None
    sender_id: int = 0
    recipient_id: int = 0
    notification_type: str = ""
    pushover_success: bool = False
    error_message: str | None = None
    created_at: datetime | None = None
