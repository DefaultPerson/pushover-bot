from aiogram import Router

from .admin import router as admin_router
from .common import router as common_router
from .events import router as events_router
from .group import router as group_router
from .private import router as private_router


def setup_routers() -> Router:
    """Setup all routers."""
    main_router = Router()
    main_router.include_router(events_router)
    main_router.include_router(admin_router)  # Admin commands first
    main_router.include_router(private_router)
    main_router.include_router(group_router)
    main_router.include_router(common_router)
    return main_router


__all__ = ["setup_routers"]
