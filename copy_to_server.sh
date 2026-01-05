#!/bin/bash
set -e

SERVER_IP="103.71.21.7"
SERVER_USER="root"
SERVER_PASS="24n7O5x9pNV2"
SERVER_PATH="/opt/avtoservis"

echo "=== Копирование файлов на сервер ==="

# Функция для выполнения команд на сервере
ssh_exec() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER_USER@$SERVER_IP" "$@"
}

# Функция для копирования файлов
scp_copy() {
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$1" "$SERVER_USER@$SERVER_IP:$2"
}

echo "1. Копирование Statistics.tsx..."
scp_copy "web/frontend/src/pages/Statistics.tsx" "$SERVER_PATH/web/frontend/src/pages/Statistics.tsx"
echo "✅ Statistics.tsx скопирован"

echo "2. Копирование Statistics.css..."
scp_copy "web/frontend/src/pages/Statistics.css" "$SERVER_PATH/web/frontend/src/pages/Statistics.css"
echo "✅ Statistics.css скопирован"

echo "3. Копирование скрипта исправления..."
scp_copy "fix_server.sh" "$SERVER_PATH/fix_server.sh"
echo "✅ fix_server.sh скопирован"

echo "4. Копирование оптимизированного docker-compose.yml..."
scp_copy "docker-compose.optimized.yml" "$SERVER_PATH/docker-compose.optimized.yml"
echo "✅ docker-compose.optimized.yml скопирован"

echo ""
echo "=== Файлы скопированы ==="


