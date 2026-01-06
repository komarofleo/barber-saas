                                            #!/bin/bash
# Скрипт для создания администратора через Docker

TELEGRAM_ID=329621295

echo "🔌 Создание администратора через Docker..."
echo ""

# Проверяем, запущен ли Docker
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "❌ PostgreSQL не запущен!"
    echo "💡 Запустите: docker-compose up -d"
    exit 1
fi

echo "📝 Создание/обновление администратора с Telegram ID: $TELEGRAM_ID"
echo ""

# Создаем или обновляем администратора
docker-compose exec -T postgres psql -U autoservice_user -d autoservice_db << EOF
-- Создаем или обновляем администратора
INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
VALUES ($TELEGRAM_ID, true, false, false, 'Admin', NOW(), NOW())
ON CONFLICT (telegram_id) DO UPDATE SET is_admin = true;

-- Проверяем результат
SELECT id, telegram_id, first_name, is_admin, is_master 
FROM users 
WHERE telegram_id = $TELEGRAM_ID;
EOF

echo ""
echo "============================================================"
echo "📋 ДАННЫЕ ДЛЯ ВХОДА В ВЕБ-ПАНЕЛЬ:"
echo "============================================================"
echo "   Логин: $TELEGRAM_ID"
echo "   Пароль: $TELEGRAM_ID"
echo "============================================================"
echo ""
echo "💡 Введите эти данные на странице входа:"
echo "   http://localhost:3000/login"
echo ""

