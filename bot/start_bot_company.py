#!/usr/bin/env python3
"""Скрипт для запуска бота barber77_1_bot для компании ID=8"""

import asyncio
from bot.main import run_bot_for_company

# ID компании
company_id = 8

async def main():
    """Главная функция"""
    print(f"🔄 Запускаю бота для компании ID={company_id}...")
    try:
        await run_bot_for_company(company_id)
        print(f"✅ Бот успешно запущен для компании ID={company_id}")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
