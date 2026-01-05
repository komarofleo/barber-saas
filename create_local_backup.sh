#!/bin/bash
set -e

echo "=== Создание локального бекапа ==="
date

# Определяем директорию скрипта и создаем директорию для бекапов
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
mkdir -p "$BACKUP_DIR"

# Получаем дату для бекапа
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
echo "Backup date: $BACKUP_DATE"

# 1. Бекап базы данных (если есть локальная БД)
echo "1. Проверка локальной базы данных..."
if command -v psql >/dev/null 2>&1; then
    if PGPASSWORD="${DB_PASSWORD:-}" psql -h localhost -p 5433 -U autoservice_user -d autoservice_db -c "\q" >/dev/null 2>&1; then
        echo "   Создание бекапа локальной БД..."
        PGPASSWORD="${DB_PASSWORD:-}" pg_dump -h localhost -p 5433 -U autoservice_user autoservice_db | gzip > "$BACKUP_DIR/db_backup_local_${BACKUP_DATE}.sql.gz"
        if [ -f "$BACKUP_DIR/db_backup_local_${BACKUP_DATE}.sql.gz" ]; then
            DB_SIZE=$(du -h "$BACKUP_DIR/db_backup_local_${BACKUP_DATE}.sql.gz" | cut -f1)
            echo "   ✓ База данных: $DB_SIZE"
        fi
    else
        echo "   ⚠ Локальная БД недоступна, пропускаем"
    fi
else
    echo "   ⚠ psql не найден, пропускаем бекап БД"
fi

# 2. Бекап конфигурации
echo "2. Создание бекапа конфигурации..."
tar -czf "$BACKUP_DIR/config_backup_local_${BACKUP_DATE}.tar.gz" \
    docker-compose.yml \
    .env \
    web/frontend/nginx.conf \
    web/backend/Dockerfile \
    web/frontend/Dockerfile \
    bot/Dockerfile \
    2>/dev/null || true

if [ -f "$BACKUP_DIR/config_backup_local_${BACKUP_DATE}.tar.gz" ]; then
    CONFIG_SIZE=$(du -h "$BACKUP_DIR/config_backup_local_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Конфигурация: $CONFIG_SIZE"
fi

# 3. Бекап файлов проекта
echo "3. Создание бекапа файлов проекта..."
tar -czf "$BACKUP_DIR/project_files_local_${BACKUP_DATE}.tar.gz" \
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
    --exclude='*.tar.gz' \
    web/ \
    bot/ \
    shared/ \
    2>/dev/null || true

if [ -f "$BACKUP_DIR/project_files_local_${BACKUP_DATE}.tar.gz" ]; then
    FILES_SIZE=$(du -h "$BACKUP_DIR/project_files_local_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Файлы проекта: $FILES_SIZE"
fi

# 4. Создание полного бекапа
echo "4. Создание полного бекапа..."
cd "$BACKUP_DIR"
if [ -f "db_backup_local_${BACKUP_DATE}.sql.gz" ]; then
    tar -czf "full_backup_local_${BACKUP_DATE}.tar.gz" \
        db_backup_local_${BACKUP_DATE}.sql.gz \
        config_backup_local_${BACKUP_DATE}.tar.gz \
        project_files_local_${BACKUP_DATE}.tar.gz \
        2>/dev/null || true
else
    tar -czf "full_backup_local_${BACKUP_DATE}.tar.gz" \
        config_backup_local_${BACKUP_DATE}.tar.gz \
        project_files_local_${BACKUP_DATE}.tar.gz \
        2>/dev/null || true
fi

if [ -f "full_backup_local_${BACKUP_DATE}.tar.gz" ]; then
    FULL_SIZE=$(du -h "full_backup_local_${BACKUP_DATE}.tar.gz" | cut -f1)
    echo "   ✓ Полный бекап: full_backup_local_${BACKUP_DATE}.tar.gz ($FULL_SIZE)"
else
    echo "   ⚠ Не удалось создать полный бекап"
fi

# 5. Очистка старых бекапов (оставляем последние 5)
echo "5. Очистка старых бекапов..."
cd "$BACKUP_DIR"
ls -1t full_backup_local_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t db_backup_local_*.sql.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t config_backup_local_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
ls -1t project_files_local_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
echo "   ✓ Старые бекапы удалены (оставлены последние 5)"

# 6. Статистика
echo ""
echo "=== Статистика ==="
echo "Бекап сохранен в: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*local_${BACKUP_DATE}* 2>/dev/null || true
echo ""
echo "Размер директории бекапов:"
du -sh "$BACKUP_DIR" 2>/dev/null || echo "Директория не найдена"
echo ""
echo "=== Готово ==="

