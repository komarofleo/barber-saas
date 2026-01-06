"""Скрипт для проверки состояния миграций БД."""
import asyncio
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory


async def check_migrations():
    """Проверить состояние миграций БД."""
    
    print("🔍 Проверка состояния миграций БД...\n")
    
    # Настройка Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Получаем директорию с миграциями
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    
    try:
        # Получаем текущую версию в БД
        print("📊 Текущая версия в БД:")
        command.current(alembic_cfg, verbose=True)
        
        # Получаем доступные миграции
        print("\n📁 Доступные миграции:")
        scripts = script_dir.walk_revisions()
        
        revision_count = 0
        for script in scripts:
            revision_count += 1
            print(f"\n  📌 Ревизия {script.revision}")
            print(f"     Родитель: {script.down_revision or 'начальная'}")
            print(f"     Описание: {script.doc}")
            print(f"     Файл: {script.path}")
        
        print(f"\n📈 Всего миграций: {revision_count}")
        
        # Проверяем, нужно ли применить миграции
        try:
            from alembic.runtime.environment import EnvironmentContext
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine
            
            # Создаем подключение к БД
            database_url = (
                f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            )
            
            # Заменяем asyncpg на psycopg2 для синхронного подключения
            sync_url = database_url.replace("+asyncpg", "")
            
            engine = create_engine(sync_url)
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
            
            latest_rev = script_dir.get_current_head()
            
            if current_rev == latest_rev:
                print("\n✅ Все миграции применены (актуальная версия)")
            elif current_rev is None:
                print(f"\n⚠️  Миграции не применены. Нужно применить: {latest_rev}")
                print("   Запустите: python scripts/migrate.py")
            else:
                print(f"\n⚠️  Есть отставание в миграциях")
                print(f"   Текущая версия: {current_rev}")
                print(f"   Последняя версия: {latest_rev}")
                print("   Запустите: python scripts/migrate.py")
            
        except Exception as e:
            print(f"\n❌ Ошибка при проверке версий: {e}")
            print("   Возможно, миграции еще не применены")
            print("   Запустите: python scripts/migrate.py")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке миграций: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_migrations())

