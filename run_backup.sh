#!/bin/bash
set -e

LOG_FILE="/opt/backups/backup_log_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Очистка и создание бекапа ==="
echo "Дата: $(date)"
echo "Лог файл: $LOG_FILE"
echo ""

# 1. Очистка Docker
echo "1. Очистка Docker..."
docker system prune -f
docker image prune -a -f --filter "until=168h" || true
docker volume prune -f || true
echo "✓ Docker очищен"
echo ""

# 2. Создание директории для бекапа
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/autoservis_${BACKUP_DATE}"
mkdir -p "$BACKUP_DIR"
echo "2. Создание бекапа в: $BACKUP_DIR"
echo ""

# 3. Бекап базы данных
echo "3. Бекап базы данных..."
cd /opt/avtoservis
if docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db > "$BACKUP_DIR/database.sql" 2>&1; then
    DB_SIZE=$(du -h "$BACKUP_DIR/database.sql" | cut -f1)
    echo "✓ База данных сохранена: $DB_SIZE"
else
    echo "✗ Ошибка создания бекапа БД"
fi
echo ""

# 4. Бекап файлов
echo "4. Бекап файлов проекта..."
cd /opt/avtoservis
if tar -czf "$BACKUP_DIR/files.tar.gz" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='*.log' \
    . 2>&1; then
    FILES_SIZE=$(du -h "$BACKUP_DIR/files.tar.gz" | cut -f1)
    echo "✓ Файлы сохранены: $FILES_SIZE"
else
    echo "✗ Ошибка создания бекапа файлов"
fi
echo ""

# 5. Создание итогового архива
echo "5. Создание итогового архива..."
cd "$BACKUP_DIR"
if tar -czf "/opt/backups/backup_${BACKUP_DATE}.tar.gz" . 2>&1; then
    BACKUP_SIZE=$(du -h "/opt/backups/backup_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "✓ Итоговый архив: backup_${BACKUP_DATE}.tar.gz ($BACKUP_SIZE)"
else
    echo "✗ Ошибка создания итогового архива"
fi
echo ""

# 6. Поиск и копирование на sto1
echo "6. Поиск сервера sto1..."
STO1_PATH=""
for path in /mnt/sto1 /backup/sto1 /storage/sto1 /sto1 /mnt/backup/sto1 /backup /mnt/backup; do
    if [ -d "$path" ] && [ -w "$path" ]; then
        STO1_PATH="$path"
        break
    fi
done

if [ -n "$STO1_PATH" ]; then
    echo "✓ Найден sto1: $STO1_PATH"
    if cp "/opt/backups/backup_${BACKUP_DATE}.tar.gz" "$STO1_PATH/" 2>&1; then
        echo "✓ Бекап скопирован на sto1"
        ls -lh "$STO1_PATH/backup_${BACKUP_DATE}.tar.gz"
    else
        echo "✗ Ошибка копирования на sto1"
    fi
else
    echo "⚠ Сервер sto1 не найден"
    echo "Бекап сохранен в: /opt/backups/backup_${BACKUP_DATE}.tar.gz"
fi
echo ""

# 7. Статистика
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
echo "Последние бекапы:"
ls -lht /opt/backups/backup_*.tar.gz 2>/dev/null | head -3 || echo "Нет бекапов"
echo ""
echo "=== Готово ==="
echo "Лог сохранен в: $LOG_FILE"



