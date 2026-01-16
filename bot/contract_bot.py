"""Главный бот для генерации договоров."""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.handlers.contract import router as contract_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запустить бота генерации договоров."""
    token = os.getenv("CONTRACT_BOT_TOKEN")
    if not token:
        logger.error("CONTRACT_BOT_TOKEN не найден в .env")
        raise RuntimeError("CONTRACT_BOT_TOKEN не задан")
    
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(contract_router)
    
    logger.info("Запуск бота генерации договоров...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
