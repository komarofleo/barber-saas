#!/bin/bash

# ===========================================
# AutoService SaaS - Применение миграций на сервере
# ===========================================
# Этот скрипт применяет миграции к БД на удаленном сервере
# через SSH соединение
# ===========================================

# Конфигурация
SERVER_USER="your_username"
SERVER_HOST="your_server.com"
SERVER_PATH="/path/to/avtoservis"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка конфигурации
if [[ "$SERVER_USER" == "your_username" ]]; then
    error "Пожалуйста, обновите SERVER_USER в скрипте"
    exit 1
fi

if [[ "$SERVER_HOST" == "your_server.com" ]]; then
    error "Пожалуйста, обновите SERVER_HOST в скрипте"
    exit 1
fi

info "=========================================="
info "Применение миграций БД на сервере"
info "=========================================="
echo ""

# 1. Проверяем соединение с сервером
info "Проверка соединения с сервером..."
ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_HOST} "echo 'Соединение установлено'" 2>/dev/null
if [ $? -eq 0 ]; then
    success "Соединение с сервером успешно"
else
    error "Не удалось подключиться к серверу ${SERVER_USER}@${SERVER_HOST}"
    exit 1
fi
echo ""

# 2. Переходим в директорию проекта на сервере
info "Переход в директорию проекта: ${SERVER_PATH}"
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && pwd"
if [ $? -ne 0 ]; then
    error "Директория ${SERVER_PATH} не существует"
    exit 1
fi
echo ""

# 3. Проверяем наличие Docker контейнеров
info "Проверка статуса Docker контейнеров..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10"
echo ""

# 4. Применяем миграции через Python скрипты
info "Применение миграций через Python скрипты..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH}/web/backend && python3 scripts/migrate.py"
if [ $? -eq 0 ]; then
    success "Миграции успешно применены"
else
    warning "Проблемы при применении миграций через Python скрипты"
    info "Пробуем применить через SQL скрипты..."
    ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql"
    if [ $? -eq 0 ]; then
        success "SQL скрипт создания таблиц успешно применен"
    else
        error "Не удалось применить SQL скрипт"
        exit 1
    fi
fi
echo ""

# 5. Заполняем БД начальными данными
info "Заполнение БД начальными данными..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH}/web/backend && python3 scripts/seed.py"
if [ $? -eq 0 ]; then
    success "Начальные данные успешно добавлены"
else
    warning "Проблемы при добавлении начальных данных через Python скрипты"
    info "Пробуем применить через SQL скрипты..."
    ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql"
    if [ $? -eq 0 ]; then
        success "SQL скрипт начальных данных успешно применен"
    else
        error "Не удалось применить SQL скрипт начальных данных"
        exit 1
    fi
fi
echo ""

# 6. Проверяем результат
info "Проверка созданных таблиц..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c '\dt public.*'"
echo ""

info "Проверка тарифных планов..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT id, name, price_monthly FROM plans;'"
echo ""

info "Проверка супер-администраторов..."
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT username, email, is_active FROM super_admins;'"
echo ""

# 7. Перезапускаем сервисы если нужно
read -p "Перезапустить web контейнер? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "Перезапуск web контейнера..."
    ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && docker-compose restart web"
    success "Web контейнер перезапущен"
fi

echo ""
success "=========================================="
success "Миграции успешно применены!"
success "=========================================="
echo ""
info "Данные для входа супер-администратора:"
info "  Username: admin"
info "  Email: admin@autoservice.com"
info "  Password: admin123"
warning "⚠️  Обязательно измените пароль после первого входа!"
echo ""
info "Доступные API endpoints:"
info "  Health: http://${SERVER_HOST}:8000/api/health"
info "  Plans: http://${SERVER_HOST}:8000/api/public/plans"
echo ""
info "Доступные страницы:"
info "  Frontend: http://${SERVER_HOST}:3000"
info "  Register: http://${SERVER_HOST}:3000/register"
echo ""

