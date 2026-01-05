# 🚀 DEPLOYMENT - Руководство по развертыванию

Полное руководство по развертыванию системы AutoService на production сервере.

---

## 📋 Содержание

1. [Требования](#требования)
2. [Подготовка сервера](#подготовка-сервера)
3. [Установка проекта](#установка-проекта)
4. [Конфигурация](#конфигурация)
5. [Запуск](#запуск)
6. [Проверка работы](#проверка-работы)
7. [Обновление](#обновление)
8. [Резервное копирование](#резервное-копирование)
9. [Мониторинг](#мониторинг)
10. [Решение проблем](#решение-проблем)

---

## 💻 Требования

### Минимальные требования

- **ОС:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** 2 cores
- **RAM:** 2GB минимум, 4GB рекомендуется
- **Диск:** 10GB свободного места, 20GB рекомендуется
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

### Порты

| Порт | Сервис | Доступ |
|------|--------|--------|
| 3000 | Frontend (Nginx) | Внешний |
| 8000 | Backend (FastAPI) | Внешний |
| 5433 | PostgreSQL | Только Docker network |
| 6380 | Redis | Только Docker network |

---

## 🛠️ Подготовка сервера

### 1. Обновление системы

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS
sudo yum update -y
```

### 2. Установка Docker

```bash
# Скрипт установки Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Проверка установки
docker --version
```

### 3. Установка Docker Compose

```bash
# Установка плагина
sudo apt install docker-compose-plugin

# Проверка
docker compose version
```

### 4. Создание пользователя

```bash
# Создание пользователя для приложения
sudo useradd -m -s /bin/bash autoservice

# Добавление в группу docker
sudo usermod -aG docker autoservice

# Переключение на пользователя
sudo su - autoservice
```

### 5. Настройка firewall

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend API
sudo ufw enable

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

---

## 📦 Установка проекта

### 1. Клонирование/копирование

```bash
# Переход в домашнюю директорию
cd /home/autoservice

# Git clone (если есть репозиторий)
git clone https://github.com/your-repo/autoservice.git
cd autoservice

# Или копирование через SCP
# На локальной машине:
scp -r autoservice/ autoservice@your-server:/home/autoservice/
```

### 2. Структура директорий

```bash
# Создание необходимых директорий
mkdir -p data/images
mkdir -p data/logs
mkdir -p backups

# Установка прав
chmod 755 data
chmod 755 data/images
chmod 755 data/logs
```

---

## ⚙️ Конфигурация

### 1. Создание .env файла

```bash
# Копирование примера
cp .env.example .env

# Редактирование
nano .env
```

### 2. Обязательные переменные

```env
# ==================== TELEGRAM BOT ====================
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
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
WEB_CORS_ORIGINS=http://YOUR_SERVER_IP:3000,http://localhost:3000

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

### 3. Генерация секретов

```bash
# Генерация WEB_SECRET_KEY
openssl rand -hex 32

# Генерация DB_PASSWORD
openssl rand -base64 24
```

### 4. Замена значений

```bash
# Замена YOUR_SERVER_IP на реальный IP
sed -i 's/YOUR_SERVER_IP/185.17.3.108/g' .env

# Проверка файла
cat .env | grep -v "^#" | grep -v "^$"
```

---

## 🚀 Запуск

### 1. Сборка образов

```bash
# Сборка всех образов
docker compose build

# Просмотр образов
docker images | grep autoservice
```

**Ожидаемый вывод:**
```
autoservice-bot          latest    abc123    5 minutes ago   500MB
autoservice-web          latest    def456    5 minutes ago   600MB
autoservice-web-frontend latest    ghi789    5 minutes ago   150MB
```

### 2. Запуск контейнеров

```bash
# Запуск в фоновом режиме
docker compose up -d

# Проверка статуса
docker compose ps
```

**Ожидаемый вывод:**
```
NAME                        STATUS          PORTS
autoservice_bot             running         
autoservice_web             running         0.0.0.0:8000->8000/tcp
autoservice_web_frontend    running         0.0.0.0:3000->80/tcp
autoservice_postgres        running         0.0.0.0:5433->5432/tcp
autoservice_redis           running         0.0.0.0:6380->6379/tcp
```

### 3. Инициализация базы данных

```bash
# Применение миграций
docker compose exec web alembic upgrade head

# Проверка таблиц
docker compose exec postgres psql -U autoservice_user -d autoservice_db -c "\dt"
```

### 4. Создание первого администратора

```bash
# Если есть скрипт
docker compose exec web python scripts/create_admin.py --telegram-id 329621295

# Или вручную через SQL
docker compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
UPDATE users SET is_admin = TRUE WHERE telegram_id = 329621295;
EOF
```

### 5. Заполнение начальных данных

```bash
# Создание постов
docker compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
INSERT INTO posts (number, name) VALUES
(1, 'Пост №1'),
(2, 'Пост №2'),
(3, 'Пост №3'),
(4, 'Пост №4'),
(5, 'Пост №5');
EOF

# Создание услуг
docker compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
INSERT INTO services (name, description, duration, price) VALUES
('ТО', 'Техническое обслуживание автомобиля', 60, 3000),
('Диагностика', 'Компьютерная диагностика', 30, 1500),
('Ремонт двигателя', 'Ремонт и обслуживание двигателя', 60, 5000),
('Шиномонтаж', 'Шиномонтаж и балансировка', 30, 2000),
('Кузовной ремонт', 'Ремонт кузова', 60, 8000),
('Электрика', 'Ремонт электрики', 60, 4000);
EOF

# Создание настроек
docker compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
INSERT INTO settings (key, value, description) VALUES
('accepting_bookings', 'true', 'Принимаются ли заявки'),
('work_start_time', '09:00', 'Время начала работы'),
('work_end_time', '18:00', 'Время окончания работы'),
('slot_duration', '30', 'Длительность слота в минутах'),
('enable_master_specialization', 'false', 'Учитывать специализацию мастеров'),
('reminder_day_before_time', '18:00', 'Время напоминания за день'),
('reminder_hour_before', 'true', 'Напоминание за час'),
('notify_admin_delay_minutes', '5', 'Задержка уведомления админу'),
('work_order_time', '08:00', 'Время отправки лист-наряда');
EOF
```

---

## ✅ Проверка работы

### 1. Проверка контейнеров

```bash
# Статус всех контейнеров
docker compose ps

# Логи бота
docker compose logs bot | tail -50

# Логи backend
docker compose logs web | tail -50

# Логи frontend
docker compose logs web-frontend | tail -20
```

### 2. Проверка API

```bash
# Health check
curl http://localhost:8000/api/health
# Ожидается: {"status":"ok"}

# API документация
curl http://localhost:8000/docs
# Должен вернуть HTML Swagger UI
```

### 3. Проверка веб-панели

```bash
# Frontend
curl http://localhost:3000
# Должен вернуть HTML React приложения

# Или в браузере
# http://YOUR_SERVER_IP:3000
```

### 4. Проверка Telegram бота

```
1. Откройте Telegram
2. Найдите бота: @your_bot_name
3. Отправьте /start
4. Бот должен ответить сообщением регистрации
```

### 5. Проверка базы данных

```bash
# Подключение к БД
docker compose exec postgres psql -U autoservice_user -d autoservice_db

# Проверка таблиц
\dt

# Проверка данных
SELECT * FROM services;
SELECT * FROM posts;
SELECT * FROM settings;

# Выход
\q
```

---

## 🔄 Обновление

### 1. Обновление кода

```bash
# Остановка контейнеров
docker compose down

# Обновление кода (git или scp)
git pull origin main
# или
scp -r local/changes/ autoservice@server:/home/autoservice/autoservice/

# Пересборка образов
docker compose build

# Запуск
docker compose up -d
```

### 2. Обновление только frontend

```bash
# Копирование обновленных файлов
scp -r web/frontend/src/ autoservice@server:/home/autoservice/autoservice/web/frontend/

# Пересборка только frontend
docker compose build web-frontend

# Перезапуск
docker compose stop web-frontend
docker compose rm -f web-frontend
docker compose up -d web-frontend
```

### 3. Обновление только backend

```bash
# Копирование файлов
scp -r web/backend/app/ autoservice@server:/home/autoservice/autoservice/web/backend/

# Перезапуск
docker compose restart web
```

### 4. Применение миграций БД

```bash
# Создание миграции (локально)
alembic revision --autogenerate -m "описание изменений"

# Копирование миграции на сервер
scp web/backend/alembic/versions/xxx_migration.py \
    autoservice@server:/home/autoservice/autoservice/web/backend/alembic/versions/

# Применение миграции
docker compose exec web alembic upgrade head
```

---

## 💾 Резервное копирование

### 1. Автоматический бэкап (рекомендуется)

```bash
# Создание скрипта бэкапа
nano /home/autoservice/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/autoservice/backups"

# Бэкап базы данных
docker compose exec -T postgres pg_dump -U autoservice_user -d autoservice_db > \
    $BACKUP_DIR/db_$DATE.sql

# Бэкап изображений
tar -czf $BACKUP_DIR/images_$DATE.tar.gz data/images/

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Права на выполнение
chmod +x /home/autoservice/backup.sh

# Добавление в cron (ежедневно в 02:00)
crontab -e
```

```cron
0 2 * * * /home/autoservice/backup.sh >> /home/autoservice/data/logs/backup.log 2>&1
```

### 2. Ручной бэкап

```bash
# Бэкап базы данных
docker compose exec postgres pg_dump -U autoservice_user -d autoservice_db > \
    backups/db_$(date +%Y%m%d_%H%M%S).sql

# Бэкап кода
tar -czf backups/code_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='data/logs' \
    .

# Бэкап изображений
tar -czf backups/images_$(date +%Y%m%d_%H%M%S).tar.gz data/images/
```

### 3. Восстановление из бэкапа

```bash
# Остановка контейнеров
docker compose down

# Восстановление БД
docker compose up -d postgres
sleep 5
docker compose exec -T postgres psql -U autoservice_user -d autoservice_db < \
    backups/db_20251227_020000.sql

# Восстановление изображений
tar -xzf backups/images_20251227_020000.tar.gz

# Запуск всех контейнеров
docker compose up -d
```

---

## 📊 Мониторинг

### 1. Логирование

```bash
# Просмотр логов в реальном времени
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

### 2. Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
df -h
du -sh /home/autoservice/autoservice/*
```

### 3. Проверка состояния сервисов

```bash
# Скрипт проверки здоровья
nano /home/autoservice/healthcheck.sh
```

```bash
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
```

```bash
chmod +x /home/autoservice/healthcheck.sh

# Добавление в cron (каждые 5 минут)
*/5 * * * * /home/autoservice/healthcheck.sh >> /home/autoservice/data/logs/health.log 2>&1
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

# Проверка nginx конфигурации
docker compose exec web-frontend nginx -t

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
du -sh /home/autoservice/autoservice/*

# Очистка старых логов Docker
docker system prune -a

# Очистка старых бэкапов
find /home/autoservice/backups -mtime +30 -delete

# Очистка логов приложения
rm -rf /home/autoservice/autoservice/data/logs/*
```

---

## 🔒 Безопасность

### 1. SSL/TLS (рекомендуется)

```bash
# Установка Certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Обновление nginx.conf для HTTPS
# (добавьте конфигурацию SSL в web/frontend/nginx.conf)

# Автообновление сертификата
sudo crontab -e
0 0 1 * * certbot renew --quiet
```

### 2. Обновление паролей

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

### 3. Ограничение доступа

```bash
# Закрытие портов PostgreSQL и Redis от внешнего мира
# В docker-compose.yml удалите проброс портов для postgres и redis

# Разрешение доступа только с определенных IP
sudo ufw allow from 192.168.1.0/24 to any port 3000
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs -f`
2. Запустите healthcheck: `./healthcheck.sh`
3. Проверьте документацию: `README.md`, `TROUBLESHOOTING.md`
4. Проверьте конфигурацию: `docker compose config`

---

**Версия:** 1.0.0  
**Последнее обновление:** 27 декабря 2025