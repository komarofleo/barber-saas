# Руководство по настройке переменных окружения

## 📋 Обзор

Этот файл содержит инструкции по настройке переменных окружения для AutoService SaaS платформы.

## 🚀 Быстрая настройка

### 1. Создайте файл .env

```bash
# В корневой директории проекта
cp .env.example .env

# Или создайте вручную
touch .env
```

### 2. Обязательные переменные окружения

Минимальный набор переменных для запуска:

```bash
# База данных
DB_HOST=postgres
DB_PORT=5432
DB_NAME=autoservice_db
DB_USER=autoservice_user
DB_PASSWORD=your_secure_password_here

# Telegram Bot (для первой компании)
BOT_TOKEN=your_telegram_bot_token_from_botfather

# Backend
WEB_SECRET_KEY=your_super_secret_key_here_min_32_characters_long
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_CORS_ORIGINS=http://localhost:3000

# Супер-администратор
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_EMAIL=admin@autoservice.com
SUPER_ADMIN_PASSWORD=admin123
```

### 3. Генерация секретного ключа

Для генерации безопасного секретного ключа:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Пример вывода:
```
K3s9m2N1p7Q5v8R6x2Y4z1A5b8c3d6e9f0g1h2i3j4k
```

## 📝 Полный список переменных окружения

### БАЗА ДАННЫХ

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `DB_HOST` | Хост PostgreSQL | `postgres` | ✅ |
| `DB_PORT` | Порт PostgreSQL | `5432` | ✅ |
| `DB_NAME` | Имя базы данных | `autoservice_db` | ✅ |
| `DB_USER` | Имя пользователя БД | `autoservice_user` | ✅ |
| `DB_PASSWORD` | Пароль пользователя БД | `secure_password_123` | ✅ |

### ТЕЛЕГРАМ БОТ

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `BOT_TOKEN` | Токен бота (от BotFather) | `123456789:ABC...XYZ` | ✅ |
| `ADMIN_IDS` | ID администраторов (через запятую) | `123456789,987654321` | ❌ |

### WEB БЭКЕНД (FastAPI)

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `WEB_SECRET_KEY` | Секретный ключ для JWT | `K3s9m...j4k` | ✅ |
| `WEB_HOST` | Хост сервера | `0.0.0.0` | ❌ |
| `WEB_PORT` | Порт сервера | `8000` | ❌ |
| `WEB_CORS_ORIGINS` | CORS origins (через запятую) | `http://localhost:3000` | ❌ |

### YOOKASSA (Платежная система)

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `YOOKASSA_SHOP_ID` | Shop ID из Юкассы | `123456` | ✅ |
| `YOOKASSA_SECRET_KEY` | Секретный ключ из Юкассы | `test_secret_key` | ✅ |
| `YOOKASSA_API_URL` | URL API Юкассы | `https://api.yookassa.ru/v3/payments` | ❌ |

### WEBHOOK

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `WEBHOOK_RETURN_URL` | URL возврата после оплаты | `http://localhost:3000/register/success` | ✅ |
| `WEBHOOK_URL` | URL для webhook Юкассы | `http://localhost:8000/api/public/webhooks/yookassa` | ✅ |

### EMAIL (SMTP)

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `SMTP_SERVER` | SMTP сервер | `smtp.gmail.com` | ✅ |
| `SMTP_PORT` | Порт SMTP | `587` | ✅ |
| `SMTP_USERNAME` | Email для отправки | `your_email@gmail.com` | ✅ |
| `SMTP_PASSWORD` | Пароль или App Password | `your_app_password` | ✅ |
| `EMAIL_FROM` | Отправитель писем | `noreply@autoservice.com` | ✅ |

### REDIS

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `REDIS_HOST` | Хост Redis | `redis` | ❌ |
| `REDIS_PORT` | Порт Redis | `6379` | ❌ |
| `REDIS_PASSWORD` | Пароль Redis | `` | ❌ |

### CELERY

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `CELERY_BROKER_URL` | Брокер сообщений | `redis://redis:6379/0` | ❌ |
| `CELERY_RESULT_BACKEND` | Backend для результатов | `redis://redis:6379/1` | ❌ |

### СУПЕР-АДМИНИСТРАТОР

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `SUPER_ADMIN_USERNAME` | Имя пользователя | `admin` | ❌ |
| `SUPER_ADMIN_EMAIL` | Email супер-админа | `admin@autoservice.com` | ❌ |
| `SUPER_ADMIN_PASSWORD` | Пароль | `admin123` | ❌ |
| `SUPER_ADMIN_TELEGRAM_ID` | Telegram ID (необязательно) | `123456789` | ❌ |

### НАСТРОЙКИ АВТОСЕРВИСА

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `WORK_START_TIME` | Время начала рабочего дня | `09:00` | ❌ |
| `WORK_END_TIME` | Время конца рабочего дня | `20:00` | ❌ |
| `SLOT_DURATION` | Длительность слота (мин) | `60` | ❌ |

### ДРУГИЕ НАСТРОЙКИ

| Переменная | Описание | Пример | Обязательно |
|-----------|----------|--------|-----------|
| `DEBUG` | Режим отладки | `True` | ❌ |
| `TIMEZONE` | Временная зона | `Europe/Moscow` | ❌ |
| `FRONTEND_URL` | URL фронтенда | `http://localhost:3000` | ❌ |

## 🔧 Настройка Yookassa

### 1. Регистрация в Юкасса

1. Зарегистрируйтесь на [https://yookassa.ru](https://yookassa.ru)
2. Создайте магазин в личном кабинете
3. Получите Shop ID и секретный ключ

### 2. Тестовый режим

Для тестов используйте тестовые данные:

```bash
YOOKASSA_SHOP_ID=test_shop
YOOKASSA_SECRET_KEY=test_secret_key
```

### 3. Продуктивный режим

Для продакшена используйте реальные данные из личного кабинета.

## 📧 Настройка Email (Gmail)

### 1. Включите 2FA в Google Account

1. Зайдите в настройки Google Account
2. Включите двухфакторную аутентификацию (2FA)

### 2. Создайте App Password

1. Зайдите в Google Account → Security
2. Перейдите в "2-Step Verification"
3. Прокрутите вниз и выберите "App Passwords"
4. Создайте новый пароль для "Mail"
5. Скопируйте полученный пароль

### 3. Настройте .env

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=app_password_from_step_2
EMAIL_FROM=noreply@autoservice.com
```

### 4. Тестирование Email

```bash
python -c "
import smtplib
from email.mime.text import MIMEText
import os

msg = MIMEText('Тестовое письмо')
msg['Subject'] = 'Тест AutoService'
msg['From'] = os.getenv('EMAIL_FROM')
msg['To'] = os.getenv('SMTP_USERNAME')

with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
    server.starttls()
    server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
    server.send_message(msg)
    print('Письмо отправлено успешно!')
"
```

## 🤖 Настройка Telegram Bot

### 1. Создайте бота через BotFather

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: `AutoService Bot`)
   - Введите username бота (например: `autoservice_bot`)
4. Получите токен бота (например: `123456789:ABC...XYZ`)

### 2. Настройте .env

```bash
BOT_TOKEN=123456789:ABC...XYZ
```

### 3. Получите свой Telegram ID

1. Найдите @userinfobot в Telegram
2. Отправьте команду `/start`
3. Запомните ваш Telegram ID (число)

### 4. Добавьте себя как администратора (опционально)

```bash
ADMIN_IDS=123456789,987654321
```

## 🔒 Безопасность

### 1. Не коммитьте .env в Git

Убедитесь, что `.env` добавлен в `.gitignore`:

```gitignore
# Environment variables
.env
.env.local
.env.*.local
```

### 2. Используйте разные пароли

- Разные пароли для продакшена и тестовой среды
- Длинные сложные пароли (минимум 32 символа для секретных ключей)

### 3. Хранение секретов

Для продакшена используйте:
- Docker Secrets
- Kubernetes Secrets
- AWS Secrets Manager / Azure Key Vault / Google Secret Manager
- HashiCorp Vault

## ✅ Проверка конфигурации

После настройки переменных окружения, проверьте конфигурацию:

```bash
# Проверьте загрузку конфигурации
cd web/backend
python -c "
from app.config import settings
print(f'✅ DB Host: {settings.DB_HOST}')
print(f'✅ DB Name: {settings.DB_NAME}')
print(f'✅ Web Port: {settings.PORT}')
print(f'✅ Yookassa Shop ID: {settings.YOOKASSA_SHOP_ID}')
print(f'✅ SMTP Server: {settings.SMTP_SERVER}')
print(f'✅ Super Admin Email: {os.getenv(\"SUPER_ADMIN_EMAIL\")}')
"
```

## 🧪 Разные окружения

### Локальная разработка (.env.local)

```bash
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
WEB_CORS_ORIGINS=http://localhost:3000
```

### Тестовая среда (.env.test)

```bash
DB_HOST=test-postgres
DB_NAME=autoservice_test_db
DEBUG=True
```

### Продакшен (.env.production)

```bash
DB_HOST=prod-postgres.internal
DEBUG=False
WEB_CORS_ORIGINS=https://autoservice.com
WEBHOOK_RETURN_URL=https://autoservice.com/register/success
WEBHOOK_URL=https://api.autoservice.com/api/public/webhooks/yookassa
```

## 📚 Полезные ссылки

- [YooKassa Documentation](https://yookassa.ru/developers)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)

## 🐛 Устранение проблем

### Ошибка: "Invalid Yookassa credentials"

Проверьте `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` в личном кабинете Юкассы.

### Ошибка: "SMTP authentication failed"

- Убедитесь, что включен 2FA
- Создайте новый App Password
- Проверьте правильность email и пароля

### Ошибка: "Invalid bot token"

Проверьте токен в @BotFather:
1. Отправьте `/mybots`
2. Выберите ваш бот
3. Кликните на "API Token"
4. Скопируйте и замените токен

---

**После настройки переменных окружения:**
1. Примените миграции: `python scripts/migrate.py`
2. Заполните БД данными: `python scripts/seed.py`
3. Запустите проект: `docker-compose up -d`
4. Проверьте работу: `curl http://localhost:8000/api/health`

