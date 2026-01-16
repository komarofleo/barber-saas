#!/bin/bash
# Скрипт для запуска бота barber77_1_bot на сервере

echo "🔄 Запускаю бота для компании ID=8..."

sshpass -p '0M9C31Z6Hh0w' ssh -o StrictHostKeyChecking=no root@45.144.67.47 "cd /opt/barber && python3 -m bot.main run_bot_for_company 8 &" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Бот успешно запущен!"
else
    echo "❌ Ошибка при запуске бота"
fi
