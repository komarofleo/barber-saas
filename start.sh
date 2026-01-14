#!/bin/bash

# Скрипт быстрого запуска проекта Barber SaaS

set -e

echo "🚀 Запуск проекта Barber SaaS..."
echo ""

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создаю .env из .env.example..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Файл .env создан. Пожалуйста, отредактируйте его и заполните необходимые переменные."
        echo "   Особенно важно: DB_PASSWORD, WEB_SECRET_KEY, SUPER_ADMIN_PASSWORD"
        exit 1
    else
        echo "❌ Файл .env.example не найден!"
        exit 1
    fi
fi

echo "📦 Запуск Docker контейнеров..."
docker compose up -d --build

echo "⏳ Ожидание готовности базы данных..."
sleep 5

echo "🗄️  Применение миграций базы данных..."
docker compose exec -T web python -m alembic upgrade head || {
    echo "⚠️  Ошибка при применении миграций. Продолжаю..."
}

echo "🌱 Создание начальных данных и супер-админа..."
docker compose exec -T web python scripts/seed.py || {
    echo "⚠️  Ошибка при создании начальных данных. Продолжаю..."
}

echo ""
echo "✅ Проект запущен!"
echo ""
echo "📍 Доступные сервисы:"
echo "   Frontend:        http://localhost:3000"
echo "   Backend API:     http://localhost:8000"
echo "   API Docs:        http://localhost:8000/docs"
echo "   Супер-админ:     http://localhost:3000/super-admin/login"
echo ""
echo "👑 Данные для входа супер-админа:"
echo "   Email:    admin@barber-saas.com (или из SUPER_ADMIN_EMAIL)"
echo "   Пароль:   admin123 (или из SUPER_ADMIN_PASSWORD)"
echo ""
echo "📋 Просмотр логов:"
echo "   docker compose logs -f"
echo ""
