"""Quiet hours: parsing /quiet arguments and checking whether a user is quiet now."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config import settings
from src.db.models import User

_WINDOW_RE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")
# Bounded digits keep timedelta() from overflowing before the MAX_DURATION check
_DURATION_RE = re.compile(r"^(?:(\d{1,3})h)?(?:(\d{1,5})m)?$")
MAX_DURATION = timedelta(days=7)


class QuietParseError(ValueError):
    """Invalid /quiet arguments. args[0] is the locale key of the message to show."""


@dataclass
class QuietChange:
    kind: str  # "daily", "once", "for" or "off"
    start: time | None = None
    end: time | None = None
    tz: str | None = None
    quiet_from: datetime | None = None
    quiet_to: datetime | None = None


def get_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise QuietParseError("quiet_bad_tz") from e


def _parse_window(value: str) -> tuple[time, time]:
    m = _WINDOW_RE.match(value)
    if not m:
        raise QuietParseError("quiet_usage")
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59 or (h1, m1) == (h2, m2):
        raise QuietParseError("quiet_usage")
    return time(h1, m1), time(h2, m2)


def _current_or_next_window(
    start: time, end: time, zone: ZoneInfo, now: datetime
) -> tuple[datetime, datetime]:
    """The window that is active now, or the next one if none is."""
    local_now = now.astimezone(zone)
    for offset in (-1, 0, 1):
        day = local_now.date() + timedelta(days=offset)
        window_start = datetime.combine(day, start, zone)
        end_day = day if end > start else day + timedelta(days=1)
        window_end = datetime.combine(end_day, end, zone)
        # Compare instants: same-zone comparison ignores fold and breaks on DST rollback
        if window_end.timestamp() > now.timestamp():
            return window_start, window_end
    raise AssertionError("unreachable: tomorrow's window always ends in the future")


def parse_quiet(args: str, saved_tz: str | None, now: datetime) -> QuietChange:
    """Parse '/quiet' arguments: 'HH:MM-HH:MM [TZ]', 'once HH:MM-HH:MM [TZ]', '8h', 'off'."""
    parts = args.split()
    if not parts:
        raise QuietParseError("quiet_usage")
    head = parts[0].lower()

    if head == "off" and len(parts) == 1:
        return QuietChange("off")

    duration = _DURATION_RE.match(head)
    if duration and any(duration.groups()) and len(parts) == 1:
        delta = timedelta(hours=int(duration[1] or 0), minutes=int(duration[2] or 0))
        if not timedelta(0) < delta <= MAX_DURATION:
            raise QuietParseError("quiet_usage")
        return QuietChange("for", quiet_from=now, quiet_to=now + delta)

    once = head == "once"
    window_args = parts[1:] if once else parts
    if not 1 <= len(window_args) <= 2:
        raise QuietParseError("quiet_usage")
    start, end = _parse_window(window_args[0])
    tz = window_args[1] if len(window_args) == 2 else (saved_tz or settings.default_timezone)
    zone = get_zone(tz)

    if once:
        quiet_from, quiet_to = _current_or_next_window(start, end, zone, now)
        return QuietChange("once", tz=tz, quiet_from=quiet_from, quiet_to=quiet_to)
    return QuietChange("daily", start=start, end=end, tz=tz)


def is_quiet(user: User, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if user.quiet_from and user.quiet_to and user.quiet_from <= now < user.quiet_to:
        return True
    if user.quiet_start is None or user.quiet_end is None:
        return False
    try:
        zone = get_zone(user.quiet_tz or settings.default_timezone)
    except QuietParseError:
        zone = ZoneInfo("UTC")
    local = now.astimezone(zone).time()
    start, end = user.quiet_start, user.quiet_end
    if start < end:
        return start <= local < end
    return local >= start or local < end
