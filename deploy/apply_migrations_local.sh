#!/bin/bash

# ===========================================
# AutoService SaaS - Применение миграций локально
# ===========================================
# Этот скрипт применяет миграции к БД локально
# через Docker контейнеры
# ===========================================

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

# Проверяем наличие Docker
info "Проверка наличия Docker..."
if command -v docker &> /dev/null; then
    success "Docker установлен"
    DOCKER_CMD="docker"
elif command -v podman &> /dev/null; then
    success "Podman установлен"
    DOCKER_CMD="podman"
else
    error "Docker или Podman не установлен"
    info "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo ""

# Проверяем наличие Docker Compose
info "Проверка наличия Docker Compose..."
if $DOCKER_CMD compose version &> /dev/null || docker-compose version &> /dev/null; then
    success "Docker Compose установлен"
    if $DOCKER_CMD compose version &> /dev/null; then
        COMPOSE_CMD="$DOCKER_CMD compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
else
    error "Docker Compose не установлен"
    info "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo ""

# Проверяем наличие .env файла
info "Проверка наличия .env файла..."
if [ -f ".env" ]; then
    success ".env файл найден"
else
    warning ".env файл не найден"
    read -p "Создать .env файл из .env.example? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.example .env
        success ".env файл создан"
        warning "Пожалуйста, отредактируйте .env файл с вашими настройками"
        info "nano .env"
        exit 0
    else
        error ".env файл не найден. Создайте его из .env.example"
        exit 1
    fi
fi
echo ""

# Проверяем статус контейнеров
info "Проверка статуса Docker контейнеров..."
$COMPOSE_CMD ps
echo ""

# Проверяем, запущен ли PostgreSQL
info "Проверка статуса PostgreSQL контейнера..."
if $DOCKER_CMD ps --format '{{.Names}}' | grep -q 'autoservice_postgres'; then
    success "PostgreSQL контейнер запущен"
else
    warning "PostgreSQL контейнер не запущен"
    info "Запуск PostgreSQL контейнера..."
    $COMPOSE_CMD up -d postgres
    sleep 5
    success "PostgreSQL контейнер запущен"
fi
echo ""

# Проверяем наличие скриптов миграций
info "Проверка наличия скриптов миграций..."
if [ -f "web/backend/scripts/migrate.py" ]; then
    success "migrate.py найден"
else
    error "migrate.py не найден в web/backend/scripts/"
    exit 1
fi

if [ -f "web/backend/scripts/seed.py" ]; then
    success "seed.py найден"
else
    error "seed.py не найден в web/backend/scripts/"
    exit 1
fi
echo ""

# Применяем миграции
info "=========================================="
info "Применение миграций БД"
info "=========================================="
echo ""

# Выбор способа применения миграций
echo "Выберите способ применения миграций:"
echo "1) Python скрипты (рекомендуется)"
echo "2) SQL скрипты (альтернатива)"
echo "3) Alembic CLI"
echo "4) Применить все способы (попробовать по очереди)"
read -p "Ваш выбор (1-4): " -n 1 -r
echo
echo ""

case $REPLY in
    1)
        info "Применение миграций через Python скрипты..."
        $DOCKER_CMD exec autoservice_web python3 scripts/migrate.py
        if [ $? -eq 0 ]; then
            success "Миграции успешно применены через Python скрипты"
        else
            error "Ошибка при применении миграций через Python скрипты"
            exit 1
        fi
        ;;
    2)
        info "Применение миграций через SQL скрипты..."
        if [ -f "sql/create_multi_tenant_tables.sql" ]; then
            $DOCKER_CMD exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql
            if [ $? -eq 0 ]; then
                success "SQL скрипт создания таблиц успешно применен"
            else
                error "Ошибка при применении SQL скрипта создания таблиц"
                exit 1
            fi
        else
            error "SQL скрипт не найден: sql/create_multi_tenant_tables.sql"
            exit 1
        fi
        ;;
    3)
        info "Применение миграций через Alembic CLI..."
        $DOCKER_CMD exec autoservice_web alembic upgrade head
        if [ $? -eq 0 ]; then
            success "Миграции успешно применены через Alembic CLI"
        else
            error "Ошибка при применении миграций через Alembic CLI"
            exit 1
        fi
        ;;
    4)
        info "Применение миграций через все способы (пробуем по очереди)..."
        
        # Способ 1: Python скрипты
        info "Способ 1: Python скрипты..."
        $DOCKER_CMD exec autoservice_web python3 scripts/migrate.py
        if [ $? -eq 0 ]; then
            success "Миграции применены через Python скрипты"
        else
            warning "Python скрипты не сработали, пробуем SQL скрипты..."
            
            # Способ 2: SQL скрипты
            info "Способ 2: SQL скрипты..."
            $DOCKER_CMD exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql
            if [ $? -eq 0 ]; then
                success "Миграции применены через SQL скрипты"
            else
                warning "SQL скрипты не сработали, пробуем Alembic CLI..."
                
                # Способ 3: Alembic CLI
                info "Способ 3: Alembic CLI..."
                $DOCKER_CMD exec autoservice_web alembic upgrade head
                if [ $? -eq 0 ]; then
                    success "Миграции применены через Alembic CLI"
                else
                    error "Ни один из способов не сработал"
                    exit 1
                fi
            fi
        fi
        ;;
    *)
        error "Неверный выбор. Пожалуйста, выберите от 1 до 4"
        exit 1
        ;;
esac
echo ""

# Заполняем БД начальными данными
info "Заполнение БД начальными данными..."
read -p "Применить начальные данные (seed)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $DOCKER_CMD exec autoservice_web python3 scripts/seed.py
    if [ $? -eq 0 ]; then
        success "Начальные данные успешно добавлены"
    else
        warning "Ошибка при добавлении начальных данных через Python скрипты"
        info "Пробуем применить через SQL скрипты..."
        
        if [ -f "sql/seed_data.sql" ]; then
            $DOCKER_CMD exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql
            if [ $? -eq 0 ]; then
                success "Начальные данные добавлены через SQL скрипты"
            else
                error "Ошибка при добавлении начальных данных"
                exit 1
            fi
        else
            error "SQL скрипт не найден: sql/seed_data.sql"
            exit 1
        fi
    fi
else
    warning "Начальные данные не применены"
fi
echo ""

# Проверяем результат
info "=========================================="
info "Проверка результата"
info "=========================================="
echo ""

# Проверяем созданные таблицы
info "Проверка созданных таблиц..."
$DOCKER_CMD exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c '\dt public.*'
echo ""

# Проверяем тарифные планы
info "Проверка тарифных планов..."
$DOCKER_CMD exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT id, name, price_monthly FROM plans;'
echo ""

# Проверяем супер-администраторов
info "Проверка супер-администраторов..."
$DOCKER_CMD exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT username, email, is_active FROM super_admins;'
echo ""

# Перезапуск web контейнера
read -p "Перезапустить web контейнер? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "Перезапуск web контейнера..."
    $COMPOSE_CMD restart web
    sleep 3
    success "Web контейнер перезапущен"
fi
echo ""

# Итог
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
info "  Health: http://localhost:8000/api/health"
info "  Plans: http://localhost:8000/api/public/plans"
echo ""
info "Доступные страницы:"
info "  Frontend: http://localhost:3000"
info "  Register: http://localhost:3000/register"
echo ""
info "Полезные команды:"
info "  Логи web: $COMPOSE_CMD logs -f web"
info "  Логи postgres: $COMPOSE_CMD logs -f postgres"
info "  Статус: $COMPOSE_CMD ps"
info "  Перезапуск: $COMPOSE_CMD restart web"
echo ""

