#!/usr/bin/env python3
"""
Скрипт для синхронизации данных из сервера в локальную БД
Экспортирует данные через SSH и импортирует через asyncpg
"""
import os
import sys
import subprocess
import tempfile
import asyncio
import asyncpg
import re
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Параметры сервера
SERVER_IP = "103.71.21.7"
SERVER_USER = "root"
SERVER_PASS = "24n7O5x9pNV2"
SERVER_PATH = "/opt/avtoservis"

# Параметры локальной БД
LOCAL_DB_HOST = os.getenv("DB_HOST", "localhost")
LOCAL_DB_PORT = int(os.getenv("DB_PORT", "5432"))
LOCAL_DB_NAME = os.getenv("DB_NAME", "autoservice_db")
LOCAL_DB_USER = os.getenv("DB_USER", "autoservice_user")
LOCAL_DB_PASSWORD = os.getenv("DB_PASSWORD", "")

if not LOCAL_DB_PASSWORD:
    print("❌ Ошибка: DB_PASSWORD не найден в .env файле")
    sys.exit(1)


def ssh_exec(command):
    """Выполнение команды на сервере через SSH"""
    cmd = [
        'sshpass', '-p', SERVER_PASS,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'{SERVER_USER}@{SERVER_IP}',
        command
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Ошибка выполнения команды на сервере: {result.stderr}")
        sys.exit(1)
    return result.stdout


async def import_sql_file(conn, sql_file, is_structure=False):
    """Импорт SQL файла в БД через asyncpg"""
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Для структуры используем более простой подход - разбиваем по ; вне кавычек
    if is_structure:
        # Удаляем SET команды, которые могут вызывать проблемы
        lines = content.split('\n')
        filtered_lines = []
        skip_next = False
        for line in lines:
            stripped = line.strip()
            # Пропускаем SET команды и некоторые служебные команды
            if stripped.startswith('SET ') or stripped.startswith('SELECT pg_catalog'):
                continue
            if stripped.startswith('\\'):
                continue
            if '--' in line:
                line = line[:line.index('--')]
            if line.strip():
                filtered_lines.append(line)
        
        content = '\n'.join(filtered_lines)
    
    # Разбиваем на команды по точке с запятой
    # Простой парсер: ищем ; которые не внутри строк
    commands = []
    current = []
    in_string = False
    string_char = None
    i = 0
    
    while i < len(content):
        char = content[i]
        
        if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None
        
        current.append(char)
        
        if char == ';' and not in_string:
            command = ''.join(current).strip()
            if command and not command.startswith('--'):
                # Убираем точку с запятой
                command = command.rstrip(';').strip()
                if command:
                    commands.append(command)
            current = []
        
        i += 1
    
    # Если осталось что-то без точки с запятой
    if current:
        command = ''.join(current).strip()
        if command and not command.startswith('--'):
            commands.append(command)
    
    # Выполняем команды
    imported = 0
    errors = 0
    for cmd in commands:
        if not cmd or cmd.startswith('--'):
            continue
        try:
            await conn.execute(cmd)
            imported += 1
        except Exception as e:
            errors += 1
            # Игнорируем ошибки дубликатов и некоторые служебные ошибки
            error_str = str(e).lower()
            ignore_errors = [
                'duplicate key', 'unique constraint', 'already exists',
                'does not exist', 'permission denied', 'syntax error'
            ]
            if not any(ignore in error_str for ignore in ignore_errors):
                if errors <= 5:  # Показываем только первые 5 ошибок
                    print(f"      ⚠️  Ошибка: {str(e)[:150]}")
    
    if errors > 5:
        print(f"      ⚠️  ... и еще {errors - 5} ошибок")
    
    return imported


async def main():
    """Основная функция синхронизации"""
    print("=== Синхронизация данных с сервера ===\n")
    
    temp_file = None
    
    try:
        # 1. Экспорт данных с сервера
        print("1. Экспорт данных с сервера...")
        
        # Сначала экспортируем структуру (если таблиц нет)
        print("   📋 Проверяю структуру БД...")
        structure_cmd = f"""
        cd {SERVER_PATH} && docker compose exec -T postgres pg_dump -U autoservice_user -d autoservice_db \\
            --schema-only \\
            --table=users \\
            --table=clients \\
            --table=bookings \\
            --table=services \\
            --table=masters \\
            --table=posts
        """
        
        # Экспортируем данные
        export_cmd = f"""
        cd {SERVER_PATH} && docker compose exec -T postgres pg_dump -U autoservice_user -d autoservice_db \\
            --data-only \\
            --table=users \\
            --table=clients \\
            --table=bookings \\
            --table=services \\
            --table=masters \\
            --table=posts \\
            --column-inserts
        """
        
        print("   📤 Экспортирую данные...")
        exported_data = ssh_exec(export_cmd)
        
        if not exported_data.strip():
            print("   ⚠️  Данные не получены с сервера")
            sys.exit(1)
        
        print(f"   ✅ Получено {len(exported_data)} байт данных")
        
        # 2. Сохраняем во временный файл
        print("\n2. Подготовка данных...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
            f.write(exported_data)
            temp_file = f.name
        
        print(f"   ✅ Данные сохранены во временный файл")
        
        # 3. Подключение к локальной БД
        print("\n3. Подключение к локальной БД...")
        
        try:
            conn = await asyncpg.connect(
                host=LOCAL_DB_HOST,
                port=LOCAL_DB_PORT,
                database=LOCAL_DB_NAME,
                user=LOCAL_DB_USER,
                password=LOCAL_DB_PASSWORD
            )
            print("   ✅ Подключено к локальной БД")
            
            # Проверяем наличие таблиц
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'clients', 'bookings')
            """)
            
            if len(tables) < 3:
                print("   ⚠️  Таблицы не найдены в локальной БД")
                print("   📋 Создаю структуру таблиц...")
                
                # Экспортируем и применяем структуру
                structure_data = ssh_exec(structure_cmd)
                if structure_data.strip():
                    # Сохраняем структуру во временный файл и применяем
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
                        f.write(structure_data)
                        structure_file = f.name
                    
                    # Применяем структуру
                    print(f"      📝 Применяю структуру из {len(structure_data)} байт...")
                    imported_structure = await import_sql_file(conn, structure_file, is_structure=True)
                    os.unlink(structure_file)
                    
                    # Проверяем, что таблицы созданы
                    tables_after = await conn.fetch("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('users', 'clients', 'bookings')
                    """)
                    
                    if len(tables_after) >= 3:
                        print(f"   ✅ Структура таблиц создана ({imported_structure} команд, найдено таблиц: {len(tables_after)})")
                    else:
                        print(f"   ❌ Не удалось создать таблицы (найдено только {len(tables_after)} из 3)")
                        print(f"      💡 Попробуйте создать структуру вручную через миграции:")
                        print(f"         cd web/backend && alembic upgrade head")
                        await conn.close()
                        if temp_file:
                            os.unlink(temp_file)
                        sys.exit(1)
                else:
                    print("   ❌ Не удалось получить структуру БД")
                    await conn.close()
                    if temp_file:
                        os.unlink(temp_file)
                    sys.exit(1)
        
        except Exception as e:
            print(f"   ❌ Ошибка подключения к локальной БД: {e}")
            print("   💡 Убедитесь, что локальная БД запущена и доступна")
            if temp_file:
                os.unlink(temp_file)
            sys.exit(1)
        
        # 4. Очистка старых данных (только если таблицы существуют)
        print("\n4. Очистка старых данных...")
        
        try:
            # Проверяем наличие таблиц перед очисткой
            table_check = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'clients', 'bookings')
            """)
            
            if len(table_check) >= 3:
                # Проверяем наличие данных
                try:
                    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                    if user_count > 0:
                        # Используем DELETE вместо TRUNCATE, чтобы не удалять таблицы
                        await conn.execute("DELETE FROM bookings")
                        await conn.execute("DELETE FROM clients")
                        await conn.execute("DELETE FROM users")
                        await conn.execute("DELETE FROM services")
                        await conn.execute("DELETE FROM masters")
                        await conn.execute("DELETE FROM posts")
                        print(f"   ✅ Старые данные очищены (было {user_count} пользователей)")
                    else:
                        print("   ℹ️  Данных для очистки нет")
                except Exception as e:
                    print(f"   ⚠️  Предупреждение при очистке: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("   ⚠️  Таблицы еще не созданы, пропускаю очистку")
        except Exception as e:
            print(f"   ⚠️  Предупреждение при очистке: {e}")
        
        # 5. Импорт данных
        print("\n5. Импорт данных в локальную БД...")
        
        # Проверяем таблицы перед импортом
        tables_before = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'clients', 'bookings')
        """)
        print(f"   📊 Таблиц перед импортом: {len(tables_before)}")
        
        imported = await import_sql_file(conn, temp_file, is_structure=False)
        print(f"   ✅ Импортировано команд: {imported}")
        
        # Проверяем таблицы после импорта
        tables_after = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'clients', 'bookings')
        """)
        print(f"   📊 Таблиц после импорта: {len(tables_after)}")
        
        # 6. Проверка результатов
        print("\n6. Проверка результатов...")
        
        if len(tables_after) < 3:
            print(f"   ❌ Таблицы не найдены после импорта (найдено {len(tables_after)} из 3)")
            print(f"   💡 Возможно, импорт данных удалил таблицы. Проверьте SQL файл.")
            await conn.close()
            if temp_file:
                # Сохраняем файл для отладки
                debug_file = temp_file.replace('.sql', '_debug.sql')
                import shutil
                shutil.copy(temp_file, debug_file)
                print(f"   💾 SQL файл сохранен для отладки: {debug_file}")
            sys.exit(1)
        
        # Проверяем схему таблиц
        schema_check = await conn.fetch("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('public', 'autoservice_db')
            AND table_name IN ('users', 'clients', 'bookings')
        """)
        
        if schema_check:
            schema_name = schema_check[0]['table_schema']
            print(f"   📋 Схема таблиц: {schema_name}")
        else:
            schema_name = 'public'
        
        # Используем явное указание схемы
        user_count = await conn.fetchval(f"SELECT COUNT(*) FROM {schema_name}.users")
        client_count = await conn.fetchval(f"SELECT COUNT(*) FROM {schema_name}.clients")
        booking_count = await conn.fetchval(f"SELECT COUNT(*) FROM {schema_name}.bookings")
        
        print("\n=== Результаты синхронизации ===")
        print(f"Пользователей: {user_count}")
        print(f"Клиентов: {client_count}")
        print(f"Заявок: {booking_count}")
        print("\n✅ Синхронизация завершена успешно!")
        
        await conn.close()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Синхронизация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка при синхронизации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == "__main__":
    asyncio.run(main())
