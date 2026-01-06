"""Обработчики команд и сообщений"""

from .start import router as start_router
from .client.booking import router as booking_router
from .client.calendar import router as calendar_router
from .client.my_bookings import router as my_bookings_router
from .client.profile import router as profile_router
from .booking_subscription_check import check_subscription_before_booking
