"""Главный файл Telegram бота"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database.connection import init_db, close_db
from bot.handlers.client.start import router as start_router
from bot.handlers.client.booking import router as booking_router
from bot.handlers.client.calendar import router as calendar_router
from bot.handlers.client.my_bookings import router as my_bookings_router
from bot.handlers.client.profile import router as profile_router
from bot.handlers.admin.menu import router as admin_menu_router
from bot.handlers.admin.bookings import router as admin_bookings_router
from bot.handlers.master.work_order import router as master_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Инициализация БД
    await init_db()
    logger.info("Database initialized")

    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    # Клиентские роутеры
    dp.include_router(start_router)
    dp.include_router(profile_router)  # Профиль и О нас - регистрируем раньше
    dp.include_router(booking_router)
    dp.include_router(calendar_router)
    dp.include_router(my_bookings_router)
    # Админские роутеры
    dp.include_router(admin_menu_router)
    dp.include_router(admin_bookings_router)
    # Мастерские роутеры
    dp.include_router(master_router)

    logger.info("Bot started")
    
    # Запускаем polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

