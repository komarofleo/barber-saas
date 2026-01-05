#!/usr/bin/env python3
"""Скрипт для создания/обновления администратора"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'))

async def fix_admin():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='autoservice_db',
        user='autoservice_user',
        password=os.getenv('DB_PASSWORD', '')
    )
    
    telegram_id = 329621295
    
    # Проверяем, есть ли пользователь
    user = await conn.fetchrow('SELECT * FROM users WHERE telegram_id = $1', telegram_id)
    
    if user:
        print(f'✅ Пользователь с Telegram ID {telegram_id} найден')
        print(f'   ID: {user["id"]}, Имя: {user["first_name"]}, Admin: {user["is_admin"]}')
        
        # Обновляем, если не админ
        if not user['is_admin']:
            await conn.execute('UPDATE users SET is_admin = true WHERE telegram_id = $1', telegram_id)
            print(f'✅ Пользователь назначен администратором')
        else:
            print(f'✅ Пользователь уже администратор')
    else:
        # Создаем нового пользователя-администратора
        await conn.execute('''
            INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
            VALUES ($1, true, false, false, $2, NOW(), NOW())
        ''', telegram_id, 'Admin')
        print(f'✅ Создан новый администратор с Telegram ID {telegram_id}')
    
    # Проверяем результат
    admin = await conn.fetchrow('SELECT * FROM users WHERE telegram_id = $1', telegram_id)
    print(f'\n📋 Данные для входа:')
    print(f'   Логин: {admin["telegram_id"]}')
    print(f'   Пароль: {admin["telegram_id"]}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_admin())

