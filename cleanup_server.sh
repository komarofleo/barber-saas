#!/bin/bash
set -e

echo "=== ОЧИСТКА СЕРВЕРА ==="
echo "Дата: $(date)"
echo ""

# 1. Очистка Docker
echo "1. Очистка Docker..."
echo "   - Удаление остановленных контейнеров..."
docker container prune -f > /dev/null 2>&1

echo "   - Удаление неиспользуемых образов..."
docker image prune -a -f --filter "until=168h" > /dev/null 2>&1

echo "   - Удаление неиспользуемых volumes..."
docker volume prune -f > /dev/null 2>&1

echo "   - Удаление неиспользуемых сетей..."
docker network prune -f > /dev/null 2>&1

echo "   - Полная очистка системы..."
docker system prune -a -f --volumes > /dev/null 2>&1

echo "   ✅ Docker очищен"
echo ""

# 2. Очистка логов
echo "2. Очистка логов..."
echo "   - Очистка systemd логов..."
journalctl --vacuum-time=3d > /dev/null 2>&1 || true

echo "   - Очистка старых логов в /var/log..."
find /var/log -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
find /var/log -name "*.gz" -type f -mtime +7 -delete 2>/dev/null || true

echo "   - Очистка логов Docker..."
truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null || true

echo "   ✅ Логи очищены"
echo ""

# 3. Очистка старых бекапов
echo "3. Очистка старых бекапов..."
if [ -d "/opt/backups" ]; then
    OLD_BACKUPS=$(find /opt/backups -type f -mtime +7 2>/dev/null | wc -l)
    if [ "$OLD_BACKUPS" -gt 0 ]; then
        find /opt/backups -type f -mtime +7 -delete 2>/dev/null || true
        echo "   ✅ Удалено $OLD_BACKUPS старых бекапов (старше 7 дней)"
    else
        echo "   ℹ️  Старых бекапов не найдено"
    fi
else
    echo "   ℹ️  Директория /opt/backups не существует"
fi
echo ""

# 4. Очистка временных файлов
echo "4. Очистка временных файлов..."
rm -rf /tmp/* 2>/dev/null || true
rm -rf /var/tmp/* 2>/dev/null || true
echo "   ✅ Временные файлы очищены"
echo ""

# 5. Очистка кэша пакетов
echo "5. Очистка кэша пакетов..."
if command -v apt-get > /dev/null 2>&1; then
    apt-get clean > /dev/null 2>&1 || true
    apt-get autoclean > /dev/null 2>&1 || true
    echo "   ✅ Кэш apt очищен"
elif command -v yum > /dev/null 2>&1; then
    yum clean all > /dev/null 2>&1 || true
    echo "   ✅ Кэш yum очищен"
fi
echo ""

# 6. Очистка старых ядер (если есть)
echo "6. Проверка старых ядер..."
if command -v apt-get > /dev/null 2>&1; then
    OLD_KERNELS=$(dpkg -l | grep -E 'linux-image-[0-9]' | grep -v $(uname -r) | wc -l)
    if [ "$OLD_KERNELS" -gt 0 ]; then
        echo "   ℹ️  Найдено $OLD_KERNELS старых ядер (не удаляем автоматически)"
    fi
fi
echo ""

# 7. Итоговая статистика
echo "=== РЕЗУЛЬТАТЫ ОЧИСТКИ ==="
echo ""
echo "Использование диска:"
df -h | grep -E '^/dev/|Filesystem'
echo ""
echo "Docker ресурсы:"
docker system df
echo ""
echo "✅ Очистка завершена!"


