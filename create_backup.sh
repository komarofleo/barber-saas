#!/bin/bash
set -e

echo "=== Создание бекапа ==="
date

# Создаем директорию
mkdir -p /opt/backups

# Получаем дату для бекапа
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
echo "Backup date: $BACKUP_DATE"

# 1. Бекап базы данных
echo "1. Создание бекапа базы данных..."
cd /opt/avtoservis
docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db > /opt/backups/database_${BACKUP_DATE}.sql
if [ -f /opt/backups/database_${BACKUP_DATE}.sql ]; then
    DB_SIZE=$(du -h /opt/backups/database_${BACKUP_DATE}.sql | cut -f1)
    echo "   ✓ База данных: $DB_SIZE"
else
    echo "   ✗ Ошибка создания бекапа БД"
    exit 1
fi

# 2. Бекап файлов
echo "2. Создание бекапа файлов..."
cd /opt/avtoservis
tar -czf /opt/backups/files_${BACKUP_DATE}.tar.gz \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='backups' \
    . 2>&1

if [ -f /opt/backups/files_${BACKUP_DATE}.tar.gz ]; then
    FILES_SIZE=$(du -h /opt/backups/files_${BACKUP_DATE}.tar.gz | cut -f1)
    echo "   ✓ Файлы: $FILES_SIZE"
else
    echo "   ✗ Ошибка создания бекапа файлов"
    exit 1
fi

# 3. Создание итогового архива
echo "3. Создание итогового архива..."
cd /opt/backups
tar -czf /opt/backups/backup_${BACKUP_DATE}.tar.gz \
    database_${BACKUP_DATE}.sql \
    files_${BACKUP_DATE}.tar.gz 2>&1

if [ -f /opt/backups/backup_${BACKUP_DATE}.tar.gz ]; then
    BACKUP_SIZE=$(du -h /opt/backups/backup_${BACKUP_DATE}.tar.gz | cut -f1)
    echo "   ✓ Итоговый архив: backup_${BACKUP_DATE}.tar.gz ($BACKUP_SIZE)"
else
    echo "   ✗ Ошибка создания итогового архива"
    exit 1
fi

# 4. Поиск и копирование на sto1
echo "4. Поиск сервера sto1..."
STO1_PATH=""
for path in /mnt/sto1 /backup/sto1 /storage/sto1 /sto1 /mnt/backup/sto1 /backup /mnt/backup; do
    if [ -d "$path" ] && [ -w "$path" ]; then
        STO1_PATH="$path"
        break
    fi
done

if [ -n "$STO1_PATH" ]; then
    echo "   ✓ Найден sto1: $STO1_PATH"
    cp /opt/backups/backup_${BACKUP_DATE}.tar.gz "$STO1_PATH/" 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ Скопировано на sto1"
        ls -lh "$STO1_PATH/backup_${BACKUP_DATE}.tar.gz"
    else
        echo "   ✗ Ошибка копирования на sto1"
    fi
else
    echo "   ⚠ Сервер sto1 не найден"
    echo "   Бекап сохранен в: /opt/backups/backup_${BACKUP_DATE}.tar.gz"
fi

# 5. Очистка Docker
echo "5. Очистка Docker..."
docker system prune -f > /dev/null 2>&1
docker image prune -a -f --filter "until=168h" > /dev/null 2>&1
echo "   ✓ Docker очищен"

# 6. Статистика
echo ""
echo "=== Статистика ==="
echo "Бекап: /opt/backups/backup_${BACKUP_DATE}.tar.gz"
ls -lh /opt/backups/backup_${BACKUP_DATE}.tar.gz
echo ""
echo "Свободное место:"
df -h / | tail -1
echo ""
echo "Размер бекапов:"
du -sh /opt/backups
echo ""
echo "=== Готово ==="



