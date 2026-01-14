"""
Главный файл для запуска нескольких Telegram ботов для разных компаний.

Этот модуль реализует мульти-бот систему для SaaS архитектуры:
- Каждый бот работает только со своей схемой БД (tenant)
- Контекст компании сохраняется в диспетчере
- Проверка подписки перед созданием записей
- Отдельный Dispatcher для каждой компании
- Изоляция данных между ботами
"""

import asyncio
import logging
import signal
from typing import Dict, Optional

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.database.connection import init_db, get_session
from bot.database.connection import AsyncSession
from bot.config import ADMIN_IDS

from app.models.public_models import Company
from app.services.tenant_service import TenantService

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Регистрируем роутеры
from bot.handlers.client.start import router as start_router
from bot.handlers.client.booking import router as booking_router
from bot.handlers.client.calendar import router as calendar_router
from bot.handlers.client.my_bookings import router as my_bookings_router
from bot.handlers.client.profile import router as profile_router
from bot.handlers.admin.menu import router as admin_menu_router
from bot.handlers.admin.bookings import router as admin_bookings_router
from bot.handlers.master.work_order import router as master_router

# Импортируем middleware
from bot.middleware.subscription import SubscriptionMiddleware

# Инициализируем сервис tenant
tenant_service = TenantService()

# Глобальный словарь для хранения диспетчеров по токену бота
_dispatchers_by_token: Dict[str, Dispatcher] = {}

def get_dispatcher_by_token(token: str) -> Optional[Dispatcher]:
    """Получить диспетчер по токену бота"""
    return _dispatchers_by_token.get(token)

# Глобальный словарь для хранения активных ботов
active_bots: Dict[int, Dict[str, any]] = {}

# Флаг graceful shutdown
shutdown_event = asyncio.Event()

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)


# ==================== Helper функции ====================

async def load_companies() -> list[Company]:
    """
    Загрузить все активные компании из public схемы.
    
    Returns:
        Список активных компаний
    """
    logger.info("Загрузка компаний из public схемы...")
    async for session in get_session():
        from sqlalchemy import select, and_
        result = await session.execute(
            select(Company).where(
                and_(
                    Company.is_active == True,
                    Company.telegram_bot_token.isnot(None)
                )
            )
        )
        companies = result.scalars().all()
        logger.info(f"Загружено {len(companies)} компаний")
        return companies


async def run_bot_for_company(company: Company) -> Optional[Dict[str, any]]:
    """
    Запустить бота для конкретной компании.
    
    Args:
        company: Объект компании
        
    Returns:
        Словарь с информацией о боте или None при ошибке
    """
    bot_id = company.id
    
    try:
        logger.info(f"Запуск бота для компании '{company.name}' (ID: {bot_id})")
        
        # Проверяем наличие токена
        if not company.telegram_bot_token:
            logger.warning(f"Компания {company.name} (ID: {bot_id}) не имеет токена бота")
            return None
        
        # Проверяем активность компании
        if not company.is_active:
            logger.warning(f"Компания {company.name} (ID: {bot_id}) не активна")
            return None
        
        # Проверяем статус подписки
        if company.subscription_status not in ['active', 'overdue']:
            logger.warning(
                f"Компания {company.name} (ID: {bot_id}) имеет статус подписки: {company.subscription_status}"
            )
            return None
        
        # Проверяем, существует ли tenant схема
        if not await tenant_service.tenancy_schema_exists(company.id):
            logger.warning(f"Tenant схема для компании {company.name} (ID: {bot_id}) не существует")
            return None
        
        # Создаем бота с токеном компании
        bot = Bot(token=company.telegram_bot_token)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Формируем список админов компании
        admin_ids = []
        if company.admin_telegram_id:
            admin_ids.append(company.admin_telegram_id)
        if company.telegram_admin_ids:
            admin_ids.extend(company.telegram_admin_ids)
        
        # Сохраняем контекст компании в диспетчере
        dp['company_id'] = company.id
        dp['company_name'] = company.name
        dp['schema_name'] = f'tenant_{company.id}'
        dp['can_create_bookings'] = company.can_create_bookings
        dp['subscription_status'] = company.subscription_status
        dp['subscription_end_date'] = company.subscription_end_date
        dp['admin_telegram_ids'] = admin_ids
        dp['admin_telegram_id'] = company.admin_telegram_id  # Основной админ
        
        # Сохраняем диспетчер как атрибут бота (для доступа в хендлерах)
        bot._dispatcher = dp
        
        # Сохраняем диспетчер в глобальном словаре по токену
        _dispatchers_by_token[company.telegram_bot_token] = dp
        logger.info(f"💾 Диспетчер сохранен: token={company.telegram_bot_token[:20]}..., всего диспетчеров={len(_dispatchers_by_token)}, admin_telegram_id={company.admin_telegram_id}")
        
        logger.info(
            f"Контекст бота '{company.name}': "
            f"company_id={company.id}, "
            f"schema=tenant_{company.id}, "
            f"can_create_bookings={company.can_create_bookings}, "
            f"subscription_status={company.subscription_status}, "
            f"admin_telegram_id={company.admin_telegram_id}, "
            f"admin_telegram_ids={admin_ids}"
        )
        
        # Применяем middleware для проверки статуса подписки
        subscription_middleware = SubscriptionMiddleware()
        dp.message.middleware(subscription_middleware)
        dp.callback_query.middleware(subscription_middleware)
        
        logger.info(f"SubscriptionMiddleware применен для компании '{company.name}'")
        
        # Регистрируем роутеры
        dp.include_router(start_router)
        dp.include_router(booking_router)
        dp.include_router(calendar_router)
        dp.include_router(my_bookings_router)
        dp.include_router(profile_router)
        dp.include_router(admin_menu_router)
        dp.include_router(admin_bookings_router)
        dp.include_router(master_router)
        
        # Убеждаемся, что диспетчер сохранен перед запуском polling
        logger.info(f"🔍 Проверка перед polling: диспетчеров в словаре={len(_dispatchers_by_token)}, bot._dispatcher установлен={hasattr(bot, '_dispatcher')}")
        
        # Запускаем polling с обработкой ошибок
        try:
            await dp.start_polling(bot, skip_updates=True)
            logger.info(f"Бот для компании '{company.name}' остановлен")
        except Exception as e:
            logger.error(f"Ошибка в боте компании '{company.name}': {e}", exc_info=True)
        
        # Возвращаем информацию о боте
        return {
            'company_id': company.id,
            'company_name': company.name,
            'bot': bot,
            'dispatcher': dp,
        }
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота для компании '{company.name}': {e}", exc_info=True)
        return None


async def stop_bot_for_company(bot_info: Dict[str, any]) -> None:
    """
    Остановить бота для конкретной компании.
    
    Args:
        bot_info: Информация о боте
    """
    try:
        bot = bot_info['bot']
        dispatcher = bot_info['dispatcher']
        
        logger.info(f"Остановка бота для компании '{bot_info['company_name']}'")
        
        # Отменяем все текущие задачи
        for task in asyncio.all_tasks():
            task.cancel()
        
        # Закрываем сессию бота
        await bot.session.close()
        
        logger.info(f"Бот для компании '{bot_info['company_name']}' остановлен")
        
    except Exception as e:
        logger.error(f"Ошибка при остановке бота для компании '{bot_info['company_name']}': {e}")


async def stop_all_bots():
    """Остановить всех активных ботов."""
    logger.info(f"Остановка {len(active_bots)} активных ботов...")
    
    for bot_id, bot_info in active_bots.items():
        await stop_bot_for_company(bot_info)
    
    active_bots.clear()
    logger.info("Все боты остановлены")


async def check_and_update_companies() -> None:
    """
    Проверить активные компании и остановить/запустить боты по необходимости.
    
    Эта функция вызывается периодически для динамического управления ботами.
    """
    global active_bots
    
    try:
        # Загружаем компании из БД
        companies = await load_companies()
        
        # Получаем ID активных ботов
        active_company_ids = set(active_bots.keys())
        
        # Получаем ID компаний, которые должны быть активны
        required_company_ids = {
            company.id
            for company in companies
            if company.is_active
            and company.subscription_status in ['active', 'overdue']
            and company.telegram_bot_token
        }
        
        # Боты для остановки (компании деактивированы или без подписки)
        bots_to_stop = active_company_ids - required_company_ids
        
        # Боты для запуска (новые или реактивированные компании)
        bots_to_start = required_company_ids - active_company_ids
        
        # Останавливаем боты
        for bot_id in bots_to_stop:
            if bot_id in active_bots:
                await stop_bot_for_company(active_bots[bot_id])
                del active_bots[bot_id]
                logger.info(f"Бот компании {bot_id} остановлен (компания деактивирована)")
        
        # Запускаем новые боты
        for bot_id in bots_to_start:
            company = next((c for c in companies if c.id == bot_id), None)
            if company:
                bot_info = await run_bot_for_company(company)
                if bot_info:
                    active_bots[bot_id] = company.id
                    logger.info(f"Бот компании {bot_id} запущен (новая или реактивированная компания)")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке компаний: {e}", exc_info=True)


async def start_all_bots():
    """Запустить боты для всех активных компаний."""
    global active_bots
    
    logger.info("Запуск системы Multi-Tenant Bot")
    
    try:
        # Инициализируем БД
        await init_db()
        
        # Загружаем компании
        companies = await load_companies()
        
        if not companies:
            logger.warning("Нет активных компаний для запуска ботов")
            return
        
        # Запускаем ботов для каждой компании в параллельных задачах
        tasks = []
        for company in companies:
            task = asyncio.create_task(run_bot_for_company(company))
            tasks.append((company.id, task))
        
        # Ждем запуска всех ботов
        for company_id, task in tasks:
            try:
                bot_info = await task
                if bot_info:
                    active_bots[company_id] = bot_info
            except Exception as e:
                logger.error(f"Ошибка запуска бота для компании {company_id}: {e}")
        
        logger.info(f"Запущено {len(active_bots)} ботов для {len(companies)} компаний")
        
        # Создаем задачу для периодической проверки компаний
        asyncio.create_task(periodic_company_check())
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске ботов: {e}", exc_info=True)


async def periodic_company_check():
    """
    Периодическая проверка компаний каждые 5 минут.
    
    Эта задача проверяет:
    - Появление новых компаний
    - Изменение статуса подписок
    - Деактивацию компаний
    """
    global active_bots
    
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(300)  # 5 минут
            await check_and_update_companies()
        except asyncio.CancelledError:
            logger.info("Периодическая проверка компаний остановлена")
            break
        except Exception as e:
            logger.error(f"Ошибка в периодической проверке компаний: {e}", exc_info=True)
            await asyncio.sleep(300)  # Продолжаем несмотря на ошибку


def handle_shutdown(signum, frame):
    """
    Обработчик сигна shutdown.
    
    Args:
        signum: Номер сигнала
        frame: Стек вызова
    """
    logger.info(f"Получен сигнал завершения: {signum}")
    shutdown_event.set()


# ==================== Главная функция ====================

async def main():
    """
    Главная функция запуска системы Multi-Tenant Bot.
    
    Запускает всех ботов для активных компаний с подписками.
    """
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info("╔════════════════════════════════════════════════════════╗")
    logger.info("║     Multi-Tenant Bot System v2.0                   ║")
    logger.info("╚════════════════════════════════════════════════════════╝")
    logger.info("")
    
    try:
        # Запускаем боты
        await start_all_bots()
        
        # Ждем сигнала завершения
        logger.info("Система работает. Нажмите Ctrl+C для завершения.")
        
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
        
        logger.info("Получен сигнал завершения...")
        await stop_all_bots()
        
        logger.info("Multi-Tenant Bot System остановлен.")
        
    except asyncio.CancelledError:
        logger.info("Запуск отменен пользователем")
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("=== Завершение работы ===")


if __name__ == '__main__':
    asyncio.run(main())
