#!/bin/bash
set -e

echo "=== Создание бекапа на сервере ==="
date

# Создаем директорию для бекапов
BACKUP_DIR="/opt/avtoservis/backups"
mkdir -p "$BACKUP_DIR"

# Получаем дату для бекапа
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
echo "Backup date: $BACKUP_DATE"

# 1. Бекап базы данных
echo "1. Создание бекапа базы данных..."
cd /opt/avtoservis
docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db | gzip > "$BACKUP_DIR/db_backup_${BACKUP_DATE}.sql.gz"
if [ -f "$BACKUP_DIR/db_backup_${BACKUP_DATE}.sql.gz" ]; then
    DB_SIZE=$(du -h "$BACKUP_DIR/db_backup_${BACKUP_DATE}.sql.gz" | cut -f1)
    echo "   ✓ База данных: $DB_SIZE"
else
    echo "   ✗ Ошибка создания бекапа БД"
    exit 1
fi

# 2. Бекап конфигурации
echo "2. Создание бекапа конфигурации..."
cd /opt/avtoservis
tar -czf "$BACKUP_DIR/config_backup_${BACKUP_DATE}.tar.gz" \
    docker-compose.yml \
    .env \
    web/frontend/nginx.conf \
    web/backend/Dockerfile \
    web/frontend/Dockerfile \
    bot/Dockerfile \
    2>/dev/null || true

if [ -f "$BACKUP_DIR/config_backup_${BACKUP_DATE}.tar.gz" ]; then
    CONFIG_SIZE=$(du -h "$BACKUP_DIR/config_backup_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Конфигурация: $CONFIG_SIZE"
fi

# 3. Бекап файлов проекта (без node_modules, venv и т.д.)
echo "3. Создание бекапа файлов проекта..."
cd /opt/avtoservis
tar -czf "$BACKUP_DIR/project_files_${BACKUP_DATE}.tar.gz" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='venv' \
    --exclude='.env' \
    --exclude='dist' \
    --exclude='build' \
    web/ \
    bot/ \
    shared/ \
    2>/dev/null || true

if [ -f "$BACKUP_DIR/project_files_${BACKUP_DATE}.tar.gz" ]; then
    FILES_SIZE=$(du -h "$BACKUP_DIR/project_files_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Файлы проекта: $FILES_SIZE"
fi

# 4. Создание полного бекапа
echo "4. Создание полного бекапа..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/full_backup_${BACKUP_DATE}.tar.gz" \
    db_backup_${BACKUP_DATE}.sql.gz \
    config_backup_${BACKUP_DATE}.tar.gz \
    project_files_${BACKUP_DATE}.tar.gz \
    2>/dev/null || true

if [ -f "$BACKUP_DIR/full_backup_${BACKUP_DATE}.tar.gz" ]; then
    FULL_SIZE=$(du -h "$BACKUP_DIR/full_backup_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Полный бекап: full_backup_${BACKUP_DATE}.tar.gz ($FULL_SIZE)"
else
    echo "   ⚠ Не удалось создать полный бекап"
fi

# 5. Очистка старых бекапов (оставляем последние 5)
echo "5. Очистка старых бекапов..."
cd "$BACKUP_DIR"
ls -1t full_backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t db_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t config_backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t project_files_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
echo "   ✓ Старые бекапы удалены (оставлены последние 5)"

# 6. Статистика
echo ""
echo "=== Статистика ==="
echo "Бекап сохранен в: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*${BACKUP_DATE}* 2>/dev/null || true
echo ""
echo "Свободное место на диске:"
df -h / | tail -1
echo ""
echo "Размер директории бекапов:"
du -sh "$BACKUP_DIR"
echo ""
echo "=== Готово ==="

