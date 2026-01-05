#!/bin/bash
set -e

echo "=== Диагностика и исправление сервера ==="
echo "Дата: $(date)"
echo ""

# 1. Проверка ресурсов
echo "1. Проверка ресурсов системы..."
echo "--- RAM ---"
free -h
echo ""
echo "--- CPU ---"
top -bn1 | head -5
echo ""
echo "--- Диск ---"
df -h
echo ""

# 2. Проверка Docker
echo "2. Проверка Docker контейнеров..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.CPU}}\t{{.MemUsage}}"
echo ""

# 3. Очистка Docker
echo "3. Очистка неиспользуемых Docker ресурсов..."
docker system prune -f
docker image prune -a -f --filter "until=168h" || true
docker volume prune -f || true
echo "✅ Docker очищен"
echo ""

# 4. Очистка логов
echo "4. Очистка старых логов..."
journalctl --vacuum-time=3d 2>/dev/null || true
find /var/log -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
find /var/log -name "*.gz" -type f -mtime +7 -delete 2>/dev/null || true
echo "✅ Логи очищены"
echo ""

# 5. Очистка старых бекапов
echo "5. Очистка старых бекапов..."
if [ -d "/opt/backups" ]; then
    find /opt/backups -type f -mtime +7 -delete 2>/dev/null || true
    echo "✅ Старые бекапы удалены"
else
    echo "⚠️  Директория /opt/backups не найдена"
fi
echo ""

# 6. Проверка swap
echo "6. Проверка swap..."
SWAP_SIZE=$(swapon --show | wc -l)
if [ "$SWAP_SIZE" -eq "0" ]; then
    echo "⚠️  Swap не настроен, создаю..."
    if [ ! -f /swapfile ]; then
        sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
        echo "✅ Swap создан (2GB)"
    else
        echo "⚠️  Файл /swapfile существует, но не активен"
        sudo swapon /swapfile 2>/dev/null || echo "⚠️  Не удалось активировать swap"
    fi
else
    echo "✅ Swap активен"
    swapon --show
fi
echo ""

# 7. Проверка использования ресурсов после очистки
echo "7. Финальная проверка ресурсов..."
echo "--- RAM ---"
free -h
echo ""
echo "--- Диск ---"
df -h
echo ""

echo "=== Исправление завершено ==="


