"""Главный файл Telegram бота с поддержкой множества ботов"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, ADMIN_IDS
from bot.database.connection import init_db, close_db
from bot.handlers.client.start import router as start_router
from bot.handlers.client.booking import router as booking_router
from bot.handlers.client.calendar import router as calendar_router
from bot.handlers.client.my_bookings import router as my_bookings_router
from bot.handlers.client.profile import router as profile_router
from bot.handlers.admin.menu import router as admin_menu_router
from bot.handlers.admin.bookings import router as admin_bookings_router
from bot.handlers.master.work_order import router as master_router
from bot.keyboards.admin import get_admin_keyboard
from bot.keyboards.client import get_client_keyboard
from bot.services.time_slots import TimeSlotsService
from bot.bot_manager import get_bot_manager

logger = logging.getLogger(__name__)


async def main():
    """
    Главная функция запуска всех ботов.
    
    Автоматически загружает все активные компании из БД и запускает
    для каждой компании отдельный бот в отдельном асинхронном таске.
    """
    # Инициализация БД
    await init_db()
    logger.info("Database initialized")
    
    try:
        # Получаем менеджер ботов
        bot_manager = get_bot_manager()
        
        # Запускаем боты для всех активных компаний
        bots_count = await bot_manager.start_all_bots()
        
        if bots_count > 0:
            logger.info(f"Запущено {bots_count} ботов для активных компаний")
            logger.info("Все боты успешно запущены!")
        else:
            logger.warning("Нет активных компаний для запуска ботов")
        
        # Ждем завершения всех ботов
        # При нажатии Ctrl+C боты остановятся автоматически
        await asyncio.gather(
            *[bot_instance.task for bot_instance in bot_manager.bots.values()],
            return_exceptions=True
        )
        
        logger.info("Боты завершили работу")
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
        # Останавливаем все боты при нажатии Ctrl+C
        await bot_manager.stop_all_bots()
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске ботов: {e}", exc_info=True)
        raise
    
    finally:
        # Закрываем соединение с БД
        await close_db()
        logger.info("Database connection closed")


if __name__ == "__main__":
    # Запускаем все боты
    asyncio.run(main())
