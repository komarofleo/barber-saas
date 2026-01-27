"""
Бот @barber76_bot для генерации договоров по TG ID администратора.
"""
import asyncio
import logging
import os
import signal

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.client import company_contract
from bot.handlers.client import company_registration
from bot.handlers.contract import contract as contract_router
from bot.database.connection import init_db, close_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запуск бота договоров для пользователей."""
    token = os.getenv("BARBER76_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BARBER76_BOT_TOKEN не задан")

    await init_db()

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(company_contract.router)
    dp.include_router(company_registration.router)
    dp.include_router(contract_router.router)

    stop_event = asyncio.Event()

    def _handle_stop(*_args) -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_stop)

    try:
        logger.info("🚀 Запуск @barber76_bot")
        await dp.start_polling(bot, stop_event=stop_event)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
