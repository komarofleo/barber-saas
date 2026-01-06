#!/usr/bin/env python3
"""Скрипт для создания/обновления администратора"""
import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'))

async def fix_admin():
    """Создать или обновить администратора"""
    telegram_id = 329621295
    
    # Пробуем подключиться через Docker (порт 5433) или локально (порт 5432)
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', '5433'))  # Docker использует 5433
    db_name = os.getenv('DB_NAME', 'autoservice_db')
    db_user = os.getenv('DB_USER', 'autoservice_user')
    db_password = os.getenv('DB_PASSWORD', '')
    
    print(f"🔌 Подключение к БД: {db_host}:{db_port}/{db_name}")
    
    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        print("✅ Подключение к БД успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("\n💡 Попробуйте запустить через Docker:")
        print("   docker-compose exec postgres psql -U autoservice_user -d autoservice_db")
        print("\nИли выполните SQL вручную:")
        print(f"""
        INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
        VALUES ({telegram_id}, true, false, false, 'Admin', NOW(), NOW())
        ON CONFLICT (telegram_id) DO UPDATE SET is_admin = true;
        """)
        sys.exit(1)
    
    try:
        # Проверяем, есть ли пользователь
        user = await conn.fetchrow('SELECT * FROM users WHERE telegram_id = $1', telegram_id)
        
        if user:
            print(f'\n✅ Пользователь с Telegram ID {telegram_id} найден')
            print(f'   ID: {user["id"]}')
            print(f'   Имя: {user["first_name"]}')
            print(f'   Admin: {user["is_admin"]}')
            
            # Обновляем, если не админ
            if not user['is_admin']:
                await conn.execute('UPDATE users SET is_admin = true WHERE telegram_id = $1', telegram_id)
                print(f'\n✅ Пользователь назначен администратором')
            else:
                print(f'\n✅ Пользователь уже администратор')
        else:
            # Создаем нового пользователя-администратора
            print(f'\n📝 Создание нового администратора...')
            await conn.execute('''
                INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
                VALUES ($1, true, false, false, $2, NOW(), NOW())
            ''', telegram_id, 'Admin')
            print(f'✅ Создан новый администратор с Telegram ID {telegram_id}')
        
        # Проверяем результат
        admin = await conn.fetchrow('SELECT * FROM users WHERE telegram_id = $1', telegram_id)
        
        print(f'\n{"="*60}')
        print(f'📋 ДАННЫЕ ДЛЯ ВХОДА В ВЕБ-ПАНЕЛЬ:')
        print(f'{"="*60}')
        print(f'   Логин: {admin["telegram_id"]}')
        print(f'   Пароль: {admin["telegram_id"]}')
        print(f'{"="*60}')
        print(f'\n💡 Введите эти данные на странице входа:')
        print(f'   http://localhost:3000/login')
        print()
        
    except Exception as e:
        print(f"❌ Ошибка при работе с БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_admin())
