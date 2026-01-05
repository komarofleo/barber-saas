"""Обработчики для администраторов"""
from .menu import router as menu_router
from .bookings import router as bookings_router

__all__ = ["menu_router", "bookings_router"]

