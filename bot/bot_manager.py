"""
Менеджер для управления множеством Telegram ботов.

Этот модуль предоставляет методы для:
- Автоматического запуска ботов для всех активных компаний
- Управления lifecycle ботов
- Остановки и перезапуска ботов
"""

import logging
from typing import Optional, Dict
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.database.connection import get_async_session, engine
from app.models.public_models import Company

logger = logging.getLogger(__name__)


class BotInstance:
    """
    Класс для хранения экземпляра бота и его состояния.
    """
    
    def __init__(
        self,
        company_id: int,
        bot: Bot,
        dispatcher: Dispatcher,
        task: Optional[asyncio.Task] = None
    ):
        self.company_id = company_id
        self.bot = bot
        self.dispatcher = dispatcher
        self.task = task
        
        # Сохраняем контекст в диспетчере
        self.dispatcher['company_id'] = company_id
        self.dispatcher['company_name'] = None  # Будет загружен из БД
        self.dispatcher['schema_name'] = f'tenant_{company_id:03d}'
        self.dispatcher['can_create_bookings'] = True  # Будет загружен из БД
        self.dispatcher['subscription_status'] = None  # Будет загружен из БД
        
        logger.info(f"BotInstance создан для компании {company_id}")


class BotManager:
    """
    Менеджер для управления множеством Telegram ботов.
    
    Автоматически запускает боты для всех активных компаний,
    отслеживает их состояние, обрабатывает ошибки.
    """
    
    def __init__(self):
        """Инициализация менеджера."""
        self.bots: Dict[int, BotInstance] = {}
        self.is_running = False
        
        logger.info("BotManager инициализирован")
    
    async def load_active_companies(self) -> list[Company]:
        """
        Загрузить список всех активных компаний из БД.
        
        Returns:
            Список активных компаний
        """
        from bot.database.models import Company
        
        async with get_async_session() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(Company).where(Company.is_active == True)
            )
            companies = result.scalars().all()
        
        logger.info(f"Загружено {len(companies)} активных компаний")
            return companies
    
    async def create_bot_instance(self, company: Company) -> BotInstance:
        """
        Создать экземпляр бота для компании.
        
        Args:
            company: Объект компании
        
        Returns:
            Экземпляр BotInstance
        
        Raises:
            Exception: Если у компании нет токена бота
        """
        if not company.telegram_bot_token:
            logger.warning(f"У компании {company.id} нет токена бота")
            raise Exception(f"У компании {company.id} нет токена бота")
        
        # Создаем бота
        bot = Bot(token=company.telegram_bot_token)
        
        # Создаем диспетчер
        dp = Dispatcher(storage=MemoryStorage())
        
        # Сохраняем контекст в диспетчере
        dp['company_id'] = company.id
        dp['company_name'] = company.name
        dp['schema_name'] = f'tenant_{company.id:03d}'
        dp['can_create_bookings'] = company.can_create_bookings
        dp['subscription_status'] = company.subscription_status
        
        logger.info(f"Экземпляр бота создан для компании {company.id}")
        
        return BotInstance(
            company_id=company.id,
            bot=bot,
            dispatcher=dp
        )
    
    async def start_bot(self, bot_instance: BotInstance):
        """
        Запустить бота в отдельном асинхронном таске.
        
        Args:
            bot_instance: Экземпляр бота
        
        Returns:
            Асинхронная таска для отслеживания
        """
        company_id = bot_instance.company_id
        
        async def bot_task():
            """Функция для запуска бота"""
            logger.info(f"Запуск бота для компании {company_id}")
            
            try:
                # Импортируем все хендлеры
                from bot.handlers.client import start as start_router
                from bot.handlers.client.booking import router as booking_router
                from bot.handlers.client.calendar import router as calendar_router
                from bot.handlers.client.my_bookings import router as my_bookings_router
                from bot.handlers.client.profile import router as profile_router
                from bot.handlers.admin.menu import router as admin_menu_router
                from bot.handlers.admin.bookings import router as admin_bookings_router
                from bot.handlers.master.work_order import router as master_router
                
                # Регистрируем роутеры в диспетчере
                bot_instance.dispatcher.include_router(start_router)
                bot_instance.dispatcher.include_router(booking_router)
                bot_instance.dispatcher.include_router(calendar_router)
                bot_instance.dispatcher.include_router(my_bookings_router)
                bot_instance.dispatcher.include_router(profile_router)
                bot_instance.dispatcher.include_router(admin_menu_router)
                bot_instance.dispatcher.include_router(admin_bookings_router)
                bot_instance.dispatcher.include_router(master_router)
                
                # Запускаем polling
                await bot_instance.dispatcher.start_polling(
                    bot_instance.bot,
                    skip_updates=True
                )
                
            except Exception as e:
                logger.error(f"Критическая ошибка бота {company_id}: {e}", exc_info=True)
                # Ждем перед перезапуском
                await asyncio.sleep(60)
        
        # Создаем и сохраняем таску
        task = asyncio.create_task(bot_task())
        bot_instance.task = task
        
        logger.info(f"Бот для компании {company_id} запущен в отдельном таске")
        
        return task
    
    async def stop_bot(self, bot_instance: BotInstance):
        """
        Остановить бота.
        
        Args:
            bot_instance: Экземпляр бота
        """
        if bot_instance.task and not bot_instance.task.done():
            bot_instance.task.cancel()
            logger.info(f"Бот для компании {bot_instance.company_id} остановлен")
        
        try:
            await bot_instance.bot.session.close()
        except Exception as e:
            logger.error(f"Ошибка закрытия сессии бота: {e}")
    
    async def start_all_bots(self):
        """
        Запустить боты для всех активных компаний.
        
        Returns:
            Количество запущенных ботов
        """
        if self.is_running:
            logger.warning("Боты уже запущены")
            return len(self.bots)
        
        logger.info("Запуск всех ботов для активных компаний...")
        
        # Загружаем активные компании
        companies = await self.load_active_companies()
        
        if not companies:
            logger.warning("Нет активных компаний")
            return 0
        
        # Создаем и запускаем боты для каждой компании
        for company in companies:
            try:
                bot_instance = await self.create_bot_instance(company)
                task = await self.start_bot(bot_instance)
                self.bots[company.id] = bot_instance
                
                logger.info(f"Бот для компании {company.id}: {company.name} - запущен")
                
            except Exception as e:
                logger.error(f"Ошибка создания бота для компании {company.id}: {e}")
                continue
        
        self.is_running = True
        logger.info(f"Всего запущено {len(self.bots)} ботов для активных компаний")
        
        return len(self.bots)
    
    async def stop_all_bots(self):
        """
        Остановить все боты.
        """
        logger.info("Остановка всех ботов...")
        
        for company_id, bot_instance in self.bots.items():
            await self.stop_bot(bot_instance)
        
        self.bots.clear()
        self.is_running = False
        
        logger.info("Все боты остановлены")
    
    async def restart_bot(self, company_id: int):
        """
        Перезапустить бота для конкретной компании.
        
        Args:
            company_id: ID компании
        """
        if company_id in self.bots:
            logger.info(f"Перезапуск бота для компании {company_id}")
            
            # Останавливаем старый бот
            await self.stop_bot(self.bots[company_id])
            
            # Загружаем данные компании
            from bot.database.models import Company
            from bot.database.connection import get_async_session
            
            async with get_async_session() as session:
                from sqlalchemy import select
                
                company = await session.get(Company, company_id)
            
            # Создаем и запускаем новый бот
            bot_instance = await self.create_bot_instance(company)
            task = await self.start_bot(bot_instance)
            self.bots[company_id] = bot_instance
            
            logger.info(f"Бот для компании {company_id} перезапущен")
        else:
            logger.warning(f"Бот для компании {company_id} не найден")
    
    async def get_bot_status(self, company_id: int) -> Dict[str, any]:
        """
        Получить статус бота для компании.
        
        Args:
            company_id: ID компании
        
        Returns:
            Словарь со статусом бота
        """
        if company_id not in self.bots:
            return {"status": "not_running", "running": False}
        
        bot_instance = self.bots[company_id]
        
        return {
            "status": "running",
            "running": bot_instance.task is not None and not bot_instance.task.done(),
            "company_id": bot_instance.company_id,
            "task_cancelled": bot_instance.task.cancelled() if bot_instance.task else False
        }
    
    def get_running_bots_count(self) -> int:
        """
        Получить количество запущенных ботов.
        
        Returns:
            Количество запущенных ботов
        """
        return len(self.bots)


# Создание экземпляра менеджера (singleton)
_bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """
    Получить или создать экземпляр BotManager.
    
    Returns:
        Экземпляр BotManager
    """
    global _bot_manager
    
    if _bot_manager is None:
        _bot_manager = BotManager()
    
    return _bot_manager


async def start_all_bots():
    """
    Удобная функция для запуска всех ботов.
    
    Returns:
        Количество запущенных ботов
    """
    manager = get_bot_manager()
    return await manager.start_all_bots()


async def stop_all_bots():
    """
    Удобная функция для остановки всех ботов.
    
    Returns:
        None
    """
    manager = get_bot_manager()
    await manager.stop_all_bots()


async def restart_bot(company_id: int):
    """
    Удобная функция для перезапуска бота компании.
    
    Args:
        company_id: ID компании
    
    Returns:
        None
    """
    manager = get_bot_manager()
    await manager.restart_bot(company_id)


def get_bot_status(company_id: int) -> Dict[str, any]:
    """
    Удобная функция для получения статуса бота.
    
    Args:
        company_id: ID компании
    
    Returns:
        Словарь со статусом бота
    """
    manager = get_bot_manager()
    return asyncio.run(manager.get_bot_status(company_id))

