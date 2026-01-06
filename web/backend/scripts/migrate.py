"""Скрипт для применения миграций к БД."""
import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from app.config import settings


async def run_migrations():
    """Применить миграции к базе данных."""
    
    # Настройка Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Обновляем URL подключения к БД из настроек
    database_url = (
        f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print(f"🔧 Применение миграций к БД: {database_url}")
    
    try:
        # Применяем миграции
        command.upgrade(alembic_cfg, "head")
        print("✅ Миграции успешно применены!")
        
        # Проверяем текущую версию
        command.current(alembic_cfg)
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграций: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migrations())

