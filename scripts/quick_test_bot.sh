#!/bin/bash
# Быстрый скрипт для тестирования бота barber77_1

COMPANY_ID=8
BOT_TOKEN="8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o"
BOT_USERNAME="barber77_1_bot"

echo "🤖 Тестирование бота barber77_1"
echo "================================"
echo ""

# Проверяем, что контейнеры запущены
if ! docker compose ps | grep -q "barber_postgres.*Up"; then
    echo "❌ PostgreSQL не запущен. Запустите: docker compose up -d postgres"
    exit 1
fi

# Обновляем username бота
echo "📝 Обновление username бота..."
docker compose exec -T postgres psql -U barber_user -d barber_db -c "UPDATE public.companies SET telegram_bot_username = '$BOT_USERNAME' WHERE id = $COMPANY_ID;" > /dev/null 2>&1
echo "✅ Username обновлен"

# Проверяем компанию
echo ""
echo "🔍 Информация о компании:"
docker compose exec -T postgres psql -U barber_user -d barber_db -c "SELECT id, name, telegram_bot_username, is_active, subscription_status FROM public.companies WHERE id = $COMPANY_ID;"

echo ""
echo "📤 Для отправки тестового сообщения выполните:"
echo "   docker compose exec web python scripts/test_bot_messages.py $COMPANY_ID <YOUR_TELEGRAM_ID> 'Тестовое сообщение'"
echo ""
echo "💡 Узнать свой Telegram ID: напишите @userinfobot в Telegram"
echo ""
echo "🔄 Для перезапуска бота:"
echo "   docker compose restart bot"
