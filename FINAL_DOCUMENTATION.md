# 📚 AutoService - Полная документация проекта

**Версия:** 1.0.0  
**Дата:** 29 декабря 2025  
**Статус:** Production Ready

---

## 📋 Содержание

1. [О проекте](#о-проекте)
2. [Быстрый старт](#быстрый-старт)
3. [Установка на новый сервер](#установка-на-новый-сервер)
4. [Конфигурация](#конфигурация)
5. [Запуск и проверка](#запуск-и-проверка)
6. [Резервное копирование](#резервное-копирование)
7. [Восстановление из бекапа](#восстановление-из-бекапа)
8. [Обновление проекта](#обновление-проекта)
9. [Развертывание на новый сервер](#развертывание-на-новый-сервер)
10. [Мониторинг и логи](#мониторинг-и-логи)
11. [Решение проблем](#решение-проблем)
12. [Безопасность](#безопасность)
13. [Структура проекта](#структура-проекта)

---

## 🎯 О проекте

**AutoService** - комплексная система управления записями для автосервиса с:
- 🤖 Telegram-ботом для клиентов, мастеров и администраторов
- 🌐 Веб-админ панелью с календарем и статистикой
- 📊 Детальной аналитикой и экспортом данных
- 🔔 Автоматическими уведомлениями

### Технологический стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Frontend:** React, TypeScript, Vite, Recharts
- **Bot:** Python, aiogram 3.x
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Queue:** Celery + Celery Beat
- **Deployment:** Docker, Docker Compose
- **Web Server:** Nginx

---

## 🚀 Быстрый старт

### Требования

- **ОС:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** 2 cores минимум
- **RAM:** 2GB минимум, 4GB рекомендуется
- **Диск:** 10GB свободного места
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

### Порты

| Порт | Сервис | Доступ |
|------|--------|--------|
| 3000 | Frontend (Nginx) | Внешний |
| 8000 | Backend (FastAPI) | Внешний |
| 5433 | PostgreSQL | Только Docker network |
| 6380 | Redis | Только Docker network |

### Минимальная установка

```bash
# 1. Клонирование/копирование проекта
cd /opt
git clone <repository> avtoservis
# или скопируйте файлы проекта

# 2. Создание .env файла
cd avtoservis
cp .env.example .env
nano .env

# 3. Заполнение обязательных переменных
BOT_TOKEN=your_bot_token
ADMIN_IDS=329621295
DB_PASSWORD=$(openssl rand -base64 24)
WEB_SECRET_KEY=$(openssl rand -hex 32)
WEB_CORS_ORIGINS=http://YOUR_SERVER_IP:3000

# 4. Запуск
docker compose build
docker compose up -d

# 5. Инициализация БД
docker compose exec web alembic upgrade head
```

---

## 🖥️ Установка на новый сервер

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose-plugin

# Проверка
docker --version
docker compose version

# Настройка firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
sudo ufw enable
```

### Шаг 2: Копирование файлов проекта

**С локальной машины:**

```bash
cd /Users/komarofleo/avtoservis

# Создание архива проекта
tar -czf /tmp/avtoservis_project.tar.gz \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='dist' \
    --exclude='full_backup_*.tar.gz' \
    .

# Копирование на сервер
scp /tmp/avtoservis_project.tar.gz root@NEW_SERVER_IP:/opt/
```

**На сервере:**

```bash
# Распаковка
cd /opt
mkdir -p avtoservis
cd avtoservis
tar -xzf ../avtoservis_project.tar.gz

# Создание необходимых директорий
mkdir -p data/images data/logs backups web/backend/uploads/broadcasts
chmod 755 data data/images data/logs backups
```

### Шаг 3: Создание .env файла

```bash
cd /opt/avtoservis
nano .env
```

**Минимальный .env:**

```env
# ==================== TELEGRAM BOT ====================
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=329621295

# ==================== DATABASE ====================
DB_HOST=postgres
DB_PORT=5432
DB_NAME=autoservice_db
DB_USER=autoservice_user
DB_PASSWORD=STRONG_PASSWORD_HERE_MIN_16_CHARS

# ==================== REDIS ====================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# ==================== APP SETTINGS ====================
DEBUG=False
TIMEZONE=Europe/Moscow

# ==================== WEB ADMIN PANEL ====================
WEB_SECRET_KEY=GENERATE_WITH_openssl_rand_-hex_32
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_CORS_ORIGINS=http://NEW_SERVER_IP:3000,http://localhost:3000

# ==================== WORK SCHEDULE ====================
WORK_START_TIME=09:00
WORK_END_TIME=18:00
SLOT_DURATION=30
ENABLE_MASTER_SPECIALIZATION=false

# ==================== NOTIFICATIONS ====================
REMINDER_DAY_BEFORE_TIME=18:00
REMINDER_HOUR_BEFORE=true
NOTIFY_ADMIN_DELAY_MINUTES=5
WORK_ORDER_TIME=08:00
```

**Генерация секретов:**

```bash
# Пароль БД
openssl rand -base64 24

# Секретный ключ
openssl rand -hex 32
```

### Шаг 4: Запуск проекта

```bash
cd /opt/avtoservis

# Сборка образов
docker compose build

# Запуск контейнеров
docker compose up -d

# Проверка статуса
docker compose ps
```

### Шаг 5: Инициализация базы данных

```bash
# Применение миграций
docker compose exec web alembic upgrade head

# Проверка таблиц
docker compose exec postgres psql -U autoservice_user -d autoservice_db -c "\dt"
```

---

## ⚙️ Конфигурация

### Обязательные переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `BOT_TOKEN` | Токен Telegram бота от @BotFather | `1234567890:ABC...` |
| `ADMIN_IDS` | Telegram ID администраторов (через запятую) | `329621295` |
| `DB_PASSWORD` | Пароль PostgreSQL (минимум 16 символов) | `STRONG_PASSWORD` |
| `WEB_SECRET_KEY` | Секретный ключ для JWT (32+ символов) | `hex_string_32_chars` |
| `WEB_CORS_ORIGINS` | Разрешенные домены для CORS | `http://IP:3000` |

### Полный список переменных

См. файл `md/autoservice_configuration.md` для полного списка всех переменных окружения.

---

## ✅ Запуск и проверка

### Проверка контейнеров

```bash
# Статус всех контейнеров
docker compose ps

# Должны быть запущены:
# - autoservice_postgres
# - autoservice_redis
# - autoservice_bot
# - autoservice_web
# - autoservice_frontend
# - autoservice_celery_worker
# - autoservice_celery_beat
```

### Проверка API

```bash
# Health check
curl http://localhost:8000/api/health
# Ожидается: {"status":"ok"}

# API документация
curl http://localhost:8000/docs
# Должен открыться Swagger UI
```

### Проверка Frontend

```bash
# Проверка доступности
curl http://localhost:3000
# Должен вернуть HTML React приложения

# Или откройте в браузере
# http://YOUR_SERVER_IP:3000
```

### Проверка Telegram бота

1. Откройте Telegram
2. Найдите бота по имени
3. Отправьте `/start`
4. Бот должен ответить

### Проверка базы данных

```bash
# Подключение к БД
docker compose exec postgres psql -U autoservice_user -d autoservice_db

# Проверка таблиц
\dt

# Проверка данных
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM bookings;
SELECT COUNT(*) FROM services;

# Выход
\q
```

---

## 💾 Резервное копирование

### Автоматический бекап

На сервере создан скрипт `/opt/avtoservis/backup.sh`:

```bash
# Запуск бекапа вручную
/opt/avtoservis/backup.sh
```

**Скрипт создает:**
- Бекап базы данных (сжатый SQL)
- Бекап конфигурации
- Бекап файлов проекта
- Итоговый архив со всеми бекапами

**Автоматическая очистка:** удаляет бекапы старше 7 дней

### Ручной бекап

```bash
cd /opt/avtoservis

# Бекап базы данных
docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db | \
    gzip > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Бекап файлов проекта
tar -czf backups/project_files_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='dist' \
    .
```

### Скачивание бекапа с сервера

```bash
# С локальной машины
scp root@SERVER_IP:/opt/avtoservis/backups/full_backup_*.tar.gz ./
```

---

## 🔄 Восстановление из бекапа

### Восстановление базы данных

```bash
cd /opt/avtoservis

# Остановка контейнеров (кроме postgres)
docker compose stop web bot celery-worker celery-beat

# Распаковка бекапа (если нужно)
cd backups
gunzip db_backup_YYYYMMDD_HHMMSS.sql.gz

# Восстановление БД
docker compose exec -T postgres psql -U autoservice_user -d autoservice_db < \
    backups/db_backup_YYYYMMDD_HHMMSS.sql

# Запуск всех контейнеров
docker compose up -d
```

### Восстановление файлов проекта

```bash
# Распаковка архива
cd /opt/avtoservis
tar -xzf backups/project_files_YYYYMMDD_HHMMSS.tar.gz

# Пересборка контейнеров (если нужно)
docker compose build
docker compose up -d
```

---

## 🔄 Обновление проекта

### Обновление всего проекта

```bash
cd /opt/avtoservis

# 1. Создание бекапа
/opt/avtoservis/backup.sh

# 2. Остановка контейнеров
docker compose down

# 3. Обновление кода
# Вариант A: через Git
git pull origin main

# Вариант B: через SCP (с локальной машины)
# scp -r /path/to/updated/files/* root@SERVER:/opt/avtoservis/

# 4. Пересборка образов
docker compose build

# 5. Запуск
docker compose up -d

# 6. Применение миграций (если есть)
docker compose exec web alembic upgrade head
```

### Обновление только Frontend

```bash
# 1. Копирование обновленных файлов
scp -r web/frontend/src/* root@SERVER:/opt/avtoservis/web/frontend/src/

# 2. Пересборка frontend
docker compose build web-frontend

# 3. Перезапуск
docker compose stop web-frontend
docker compose rm -f web-frontend
docker compose up -d web-frontend

# 4. Если используется системный nginx:
cd /opt/avtoservis/web/frontend
npm run build
cp -r dist/* /opt/avtoservis/frontend/dist/
systemctl reload nginx
```

### Обновление только Backend

```bash
# 1. Копирование обновленных файлов
scp -r web/backend/app/* root@SERVER:/opt/avtoservis/web/backend/app/

# 2. Перезапуск
docker compose restart web

# 3. Применение миграций (если есть)
docker compose exec web alembic upgrade head
```

---

## 🚀 Развертывание на новый сервер

### Полная инструкция

1. **Подготовка сервера** (см. [Установка на новый сервер](#установка-на-новый-сервер))

2. **Копирование файлов проекта** (см. [Шаг 2](#шаг-2-копирование-файлов-проекта))

3. **Создание .env** (см. [Шаг 3](#шаг-3-создание-env-файла))

4. **Запуск проекта** (см. [Шаг 4](#шаг-4-запуск-проекта))

5. **Восстановление данных из бекапа** (если нужно):

```bash
# Скачать бекап на новый сервер
scp full_backup_*.tar.gz root@NEW_SERVER:/opt/avtoservis/backups/

# Распаковать
cd /opt/avtoservis/backups
tar -xzf full_backup_*.tar.gz

# Восстановить БД
gunzip db_backup_*.sql.gz
docker compose exec -T postgres psql -U autoservice_user -d autoservice_db < \
    db_backup_*.sql
```

6. **Настройка системного Nginx** (если используется):

```bash
# Сборка frontend
cd /opt/avtoservis/web/frontend
npm install
npm run build

# Копирование в папку для nginx
mkdir -p /opt/avtoservis/frontend/dist
cp -r dist/* /opt/avtoservis/frontend/dist/

# Создание конфига nginx
sudo nano /etc/nginx/sites-available/autoservice
```

**Конфигурация nginx:**

```nginx
server {
    listen 3000;
    server_name _;
    root /opt/avtoservis/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Активация
sudo ln -s /etc/nginx/sites-available/autoservice /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 Мониторинг и логи

### Просмотр логов

```bash
# Все логи в реальном времени
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f bot
docker compose logs -f web
docker compose logs -f web-frontend

# Последние N строк
docker compose logs --tail=100 bot

# Логи за период
docker compose logs --since 2h bot
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
df -h
du -sh /opt/avtoservis/*

# Проверка процессов
docker compose ps
```

### Health Check скрипт

```bash
# Создание скрипта
cat > /opt/avtoservis/healthcheck.sh << 'EOF'
#!/bin/bash

# Проверка API
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
if [ $API_STATUS -eq 200 ]; then
    echo "✅ API: OK"
else
    echo "❌ API: FAILED ($API_STATUS)"
fi

# Проверка Frontend
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ $FRONTEND_STATUS -eq 200 ]; then
    echo "✅ Frontend: OK"
else
    echo "❌ Frontend: FAILED ($FRONTEND_STATUS)"
fi

# Проверка PostgreSQL
docker compose exec -T postgres pg_isready -U autoservice_user > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL: OK"
else
    echo "❌ PostgreSQL: FAILED"
fi

# Проверка Redis
docker compose exec -T redis redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAILED"
fi
EOF

chmod +x /opt/avtoservis/healthcheck.sh

# Запуск проверки
/opt/avtoservis/healthcheck.sh
```

---

## 🔧 Решение проблем

### Бот не запускается

```bash
# Проверка токена
docker compose logs bot | grep -i "token\|error"

# Проверка .env
cat .env | grep BOT_TOKEN

# Перезапуск
docker compose restart bot

# Пересборка
docker compose build bot
docker compose up -d bot
```

### Веб-панель не открывается

```bash
# Проверка контейнеров
docker compose ps

# Проверка логов
docker compose logs web-frontend | tail -50
docker compose logs web | tail -50

# Проверка nginx конфигурации (если используется системный nginx)
sudo nginx -t

# Перезапуск
docker compose restart web-frontend web
```

### База данных недоступна

```bash
# Проверка контейнера
docker compose ps postgres

# Проверка подключения
docker compose exec postgres pg_isready -U autoservice_user

# Проверка логов
docker compose logs postgres | tail -50

# Пересоздание контейнера
docker compose stop postgres
docker compose rm -f postgres
docker compose up -d postgres
```

### Ошибки при миграциях

```bash
# Просмотр текущей версии
docker compose exec web alembic current

# Просмотр истории
docker compose exec web alembic history

# Откат на одну версию назад
docker compose exec web alembic downgrade -1

# Применение конкретной версии
docker compose exec web alembic upgrade <revision>
```

### Проблемы с дисковым пространством

```bash
# Проверка использования
df -h
du -sh /opt/avtoservis/*

# Очистка старых логов Docker
docker system prune -a

# Очистка старых бекапов
find /opt/avtoservis/backups -mtime +7 -delete

# Очистка логов приложения
rm -rf /opt/avtoservis/data/logs/*
```

### Frontend не обновляется после изменений

```bash
# Если используется Docker контейнер:
docker compose build web-frontend
docker compose stop web-frontend
docker compose rm -f web-frontend
docker compose up -d web-frontend

# Если используется системный nginx:
cd /opt/avtoservis/web/frontend
npm run build
cp -r dist/* /opt/avtoservis/frontend/dist/
systemctl reload nginx

# Очистка кэша браузера (Ctrl+Shift+R или Cmd+Shift+R)
```

---

## 🔒 Безопасность

### SSL/TLS (рекомендуется)

```bash
# Установка Certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Автообновление сертификата
sudo crontab -e
# Добавить: 0 0 1 * * certbot renew --quiet
```

### Обновление паролей

```bash
# Генерация новых паролей
NEW_DB_PASSWORD=$(openssl rand -base64 24)
NEW_SECRET_KEY=$(openssl rand -hex 32)

# Обновление .env
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASSWORD/" .env
sed -i "s/WEB_SECRET_KEY=.*/WEB_SECRET_KEY=$NEW_SECRET_KEY/" .env

# Обновление пароля в PostgreSQL
docker compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
ALTER USER autoservice_user WITH PASSWORD '$NEW_DB_PASSWORD';
EOF

# Перезапуск
docker compose down
docker compose up -d
```

### Ограничение доступа

```bash
# Закрытие портов PostgreSQL и Redis от внешнего мира
# В docker-compose.yml удалите проброс портов для postgres и redis

# Разрешение доступа только с определенных IP
sudo ufw allow from 192.168.1.0/24 to any port 3000
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

---

## 📁 Структура проекта

```
avtoservis/
├── bot/                    # Telegram бот
│   ├── handlers/          # Обработчики команд
│   ├── keyboards/         # Клавиатуры
│   ├── database/          # CRUD операции
│   └── main.py           # Точка входа
├── web/                   # Веб-панель
│   ├── backend/          # FastAPI backend
│   │   ├── app/          # Приложение
│   │   │   ├── api/      # API endpoints
│   │   │   ├── services/ # Бизнес-логика
│   │   │   └── tasks/    # Celery задачи
│   │   ├── alembic/      # Миграции БД
│   │   └── main.py      # Точка входа
│   └── frontend/         # React frontend
│       ├── src/          # Исходники
│       │   ├── pages/   # Страницы
│       │   ├── components/ # Компоненты
│       │   └── api/      # API клиент
│       └── dist/         # Собранное приложение
├── shared/               # Общий код
│   └── database/        # Модели БД
├── scripts/             # Скрипты
├── data/                # Данные
│   ├── images/         # Изображения
│   └── logs/           # Логи
├── backups/            # Бекапы
├── docker-compose.yml   # Docker Compose конфигурация
├── .env                 # Переменные окружения
└── README.md           # Документация
```

---

## 📞 Поддержка

### Полезные команды

```bash
# Статус всех контейнеров
docker compose ps

# Логи всех сервисов
docker compose logs -f

# Перезапуск всех сервисов
docker compose restart

# Остановка всех сервисов
docker compose down

# Проверка конфигурации
docker compose config

# Health check
/opt/avtoservis/healthcheck.sh
```

### Дополнительная документация

- `md/autoservice_deployment.md` - Детальное руководство по развертыванию
- `md/autoservice_configuration.md` - Полная конфигурация
- `md/autoservice_api.md` - API документация
- `md/autoservice_database.md` - Структура базы данных
- `md/autoservice_user_flows.md` - Пользовательские сценарии

---

## 📝 Чеклист развертывания

- [ ] Сервер подготовлен (Docker, Docker Compose установлены)
- [ ] Файлы проекта скопированы
- [ ] Создан файл `.env` с правильными значениями
- [ ] Сгенерированы секретные ключи
- [ ] Созданы необходимые директории
- [ ] Docker образы собраны
- [ ] Контейнеры запущены
- [ ] Миграции БД применены
- [ ] Frontend собран (если используется системный nginx)
- [ ] Nginx настроен (если используется)
- [ ] Все сервисы проверены (health check)
- [ ] Бекап создан
- [ ] Firewall настроен

---

**Последнее обновление:** 29 декабря 2025  
**Версия документации:** 1.0.0


