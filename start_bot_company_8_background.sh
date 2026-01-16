#!/bin/bash
# Скрипт для запуска бота barber77_1_bot для компании ID=8 в фоновом режиме

echo "🔄 Запускаю бота для компании ID=8 в фоновом режиме..."

# Запускаем бота через nohup (он будет работать в фоновом режиме)
sshpass -p '0M9C31Z6Hh0w' ssh -o StrictHostKeyChecking=no root@45.144.67.47 "cd /opt/barber/bot && nohup python3 -m bot.main run_bot_for_company 8 > bot_company_8.log 2>&1 &"

# Ждем немного, чтобы бот запустился
sleep 3

echo "✅ Бот запущен в фоновом режиме!"
echo "📁 Логи доступны: docker compose logs -f bot --tail 50"
echo ""
echo "🔍 Проверка статуса:"
sshpass -p '0M9C31Z6Hh0w' ssh -o StrictHostKeyChecking=no root@45.144.67.47 "cd /opt/barber/bot && ps aux | grep '[p]ython.*bot.main' | grep -v grep"
