#!/bin/bash
# Скрипт для синхронизации данных из сервера в локальную БД

set -e

SERVER_IP="103.71.21.7"
SERVER_USER="root"
SERVER_PASS="24n7O5x9pNV2"
SERVER_PATH="/opt/avtoservis"

LOCAL_DB_HOST="localhost"
LOCAL_DB_PORT="5433"
LOCAL_DB_NAME="autoservice_db"
LOCAL_DB_USER="autoservice_user"

echo "=== Синхронизация данных с сервера ==="

# Функция для выполнения команд на сервере
ssh_exec() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER_USER@$SERVER_IP" "$@"
}

# Функция для получения пароля БД из .env
get_db_password() {
    if [ -f .env ]; then
        grep "^DB_PASSWORD=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'"
    else
        echo ""
    fi
}

DB_PASSWORD=$(get_db_password)

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Ошибка: DB_PASSWORD не найден в .env файле"
    exit 1
fi

echo "1. Экспорт данных с сервера..."

# Экспортируем данные о пользователях, клиентах и заявках
ssh_exec "cd $SERVER_PATH && docker compose exec -T postgres pg_dump -U autoservice_user -d autoservice_db \
    --data-only \
    --table=users \
    --table=clients \
    --table=bookings \
    --table=services \
    --table=masters \
    --table=posts \
    --column-inserts" > /tmp/server_data.sql

echo "✅ Данные экспортированы с сервера"

echo "2. Проверка локальной БД..."

# Проверяем, запущен ли локальный postgres
if ! docker compose ps postgres | grep -q "Up"; then
    echo "⚠️  Локальный postgres не запущен. Запускаю..."
    docker compose up -d postgres
    echo "⏳ Ожидание готовности БД..."
    sleep 5
fi

echo "3. Очистка старых данных в локальной БД..."

# Очищаем таблицы перед импортом (в правильном порядке из-за foreign keys)
PGPASSWORD="$DB_PASSWORD" psql -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" <<EOF
-- Отключаем проверку внешних ключей временно
SET session_replication_role = 'replica';

-- Удаляем данные в правильном порядке
TRUNCATE TABLE bookings CASCADE;
TRUNCATE TABLE clients CASCADE;
TRUNCATE TABLE users CASCADE;
TRUNCATE TABLE services CASCADE;
TRUNCATE TABLE masters CASCADE;
TRUNCATE TABLE posts CASCADE;

-- Включаем обратно
SET session_replication_role = 'origin';
EOF

echo "✅ Старые данные очищены"

echo "4. Импорт данных в локальную БД..."

# Импортируем данные
PGPASSWORD="$DB_PASSWORD" psql -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" < /tmp/server_data.sql

echo "✅ Данные импортированы"

echo "5. Проверка результатов..."

# Проверяем количество записей
USER_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -t -c "SELECT COUNT(*) FROM users;")
CLIENT_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -t -c "SELECT COUNT(*) FROM clients;")
BOOKING_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$LOCAL_DB_HOST" -p "$LOCAL_DB_PORT" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" -t -c "SELECT COUNT(*) FROM bookings;")

echo ""
echo "=== Результаты синхронизации ==="
echo "Пользователей: $USER_COUNT"
echo "Клиентов: $CLIENT_COUNT"
echo "Заявок: $BOOKING_COUNT"
echo ""
echo "✅ Синхронизация завершена успешно!"

# Очищаем временный файл
rm -f /tmp/server_data.sql

