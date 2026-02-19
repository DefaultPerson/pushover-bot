"""Broadcast service singleton holder.

This module exists to avoid circular imports between main.py and handlers.
"""

from aiogram_broadcast import BroadcastService

# Global broadcast service instance (set by main.py at startup)
broadcast_service: BroadcastService | None = None


def get_broadcast_service() -> BroadcastService | None:
    """Get current broadcast service instance."""
    return broadcast_service


def set_broadcast_service(service: BroadcastService) -> None:
    """Set broadcast service instance."""
    global broadcast_service
    broadcast_service = service
