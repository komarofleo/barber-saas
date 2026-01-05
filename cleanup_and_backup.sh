#!/bin/bash
set -e

echo "=== Очистка и создание бекапа ==="
echo "Дата: $(date)"

# 1. Очистка Docker
echo ""
echo "1. Очистка Docker..."
docker system prune -f
docker image prune -a -f --filter "until=168h"
docker volume prune -f

# 2. Очистка логов
echo ""
echo "2. Очистка логов..."
sudo journalctl --vacuum-time=7d 2>/dev/null || true
sudo find /var/log -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
sudo find /var/log -name "*.gz" -type f -mtime +30 -delete 2>/dev/null || true

# 3. Очистка старых бекапов (старше 7 дней)
echo ""
echo "3. Очистка старых бекапов..."
find /opt/backups -type f -mtime +7 -delete 2>/dev/null || true

# 4. Создание директории для бекапа
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/autoservis_${BACKUP_DATE}"
mkdir -p "$BACKUP_DIR"
echo ""
echo "4. Создание бекапа в: $BACKUP_DIR"

# 5. Бекап базы данных
echo "   - База данных..."
cd /opt/avtoservis
docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db > "$BACKUP_DIR/database.sql" 2>/dev/null
if [ -f "$BACKUP_DIR/database.sql" ]; then
    echo "     ✓ База данных сохранена ($(du -h "$BACKUP_DIR/database.sql" | cut -f1))"
else
    echo "     ✗ Ошибка создания бекапа БД"
fi

# 6. Бекап файлов
echo "   - Файлы проекта..."
cd /opt/avtoservis
tar -czf "$BACKUP_DIR/files.tar.gz" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='*.log' \
    . 2>/dev/null

if [ -f "$BACKUP_DIR/files.tar.gz" ]; then
    echo "     ✓ Файлы сохранены ($(du -h "$BACKUP_DIR/files.tar.gz" | cut -f1))"
else
    echo "     ✗ Ошибка создания бекапа файлов"
fi

# 7. Создание итогового архива
echo "   - Создание итогового архива..."
cd "$BACKUP_DIR"
tar -czf "/opt/backups/backup_${BACKUP_DATE}.tar.gz" . 2>/dev/null
if [ -f "/opt/backups/backup_${BACKUP_DATE}.tar.gz" ]; then
    BACKUP_SIZE=$(du -h "/opt/backups/backup_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "     ✓ Итоговый архив создан: backup_${BACKUP_DATE}.tar.gz ($BACKUP_SIZE)"
else
    echo "     ✗ Ошибка создания итогового архива"
fi

# 8. Поиск и копирование на sto1
echo ""
echo "5. Поиск сервера sto1..."
STO1_PATH=""
# Проверяем различные возможные пути
for path in /mnt/sto1 /backup/sto1 /storage/sto1 /sto1 /mnt/backup/sto1; do
    if [ -d "$path" ] && [ -w "$path" ]; then
        STO1_PATH="$path"
        break
    fi
done

if [ -n "$STO1_PATH" ]; then
    echo "   ✓ Найден sto1: $STO1_PATH"
    cp "/opt/backups/backup_${BACKUP_DATE}.tar.gz" "$STO1_PATH/" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✓ Бекап скопирован на sto1"
        ls -lh "$STO1_PATH/backup_${BACKUP_DATE}.tar.gz"
    else
        echo "   ✗ Ошибка копирования на sto1"
    fi
else
    echo "   ⚠ Сервер sto1 не найден или недоступен для записи"
    echo "   Бекап сохранен в: /opt/backups/backup_${BACKUP_DATE}.tar.gz"
fi

# 9. Статистика
echo ""
echo "=== Статистика ==="
echo "Свободное место:"
df -h / | tail -1
echo ""
echo "Docker использование:"
docker system df
echo ""
echo "Размер бекапов:"
du -sh /opt/backups 2>/dev/null || echo "0"
echo ""
echo "=== Готово ==="



