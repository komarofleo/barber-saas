# 🚗 AutoService SaaS - Мульти-тенантная платформа для управления автосервисами

Полнофункциональная мульти-тенантная SaaS платформа для управления автосервисами с Telegram-ботами и веб-админ панелью.

## ✨ Возможности

### 📱 Telegram Бот
- Запись на обслуживание через Telegram
- Календарь доступных слотов
- Управление своими записями
- Уведомления о записи
- Профиль клиента

### 💼 Мульти-тенантность
- Каждый клиент (автосервис) получает изолированную базу данных
- Отдельный Telegram бот для каждого клиента
- Система подписок и тарифов
- Биллинг через Юкассу
- Уведомления о подписках

### 🖥 Веб-админ панель
- Управление услугами и мастерами
- Управление записями
- Управление клиентами
- Управление маркетингом (посты, акции, промокоды)
- Статистика и аналитика
- Управление подпиской и платежами

### 👑 Супер-админ панель
- Управление всеми компаниями
- Статистика по всем клиентам
- Управление тарифными планами
- Мониторинг статусов подписок

## 🚀 Быстрый старт

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- Минимум: 4GB RAM, 20GB диск
- Аккаунт в Telegram BotFather

### Установка

1. **Создайте файл `.env`** на основе `.env.example`:
```bash
cp .env.example .env
nano .env
```

2. **Заполните обязательные переменные:**
```env
# База данных
DB_HOST=postgres
DB_PORT=5432
DB_NAME=autoservice_db
DB_USER=autoservice_user
DB_PASSWORD=your_strong_password_here

# Web
WEB_SECRET_KEY=your_32_character_secret_key_here
WEB_HOST=0.0.0.0
WEB_PORT=8000

# Юкасса (для платежей)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_API_URL=https://api.yookassa.ru/v3
YOOKASSA_RETURN_URL=https://your-domain.com/success
YOOKASSA_WEBHOOK_URL=https://your-domain.com/api/public/webhooks/yookassa

# Redis (для Celery)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Супер-админ
SUPER_ADMIN_EMAIL=admin@yourdomain.com
SUPER_ADMIN_PASSWORD=your_strong_password
SUPER_ADMIN_TELEGRAM_ID=your_telegram_id

# Супер-админ бот
SUPER_ADMIN_BOT_TOKEN=your_bot_token_from_botfather
```

3. **Запустите проект:**
```bash
docker compose build
docker compose up -d
```

4. **Инициализируйте базу данных:**
```bash
# Применить миграции
docker compose exec web python -m alembic upgrade head

# Создать начальные данные (тарифные планы, супер-админ)
docker compose exec web python scripts/seed.py
```

5. **Проверьте работу сервисов:**
```bash
# Проверить статус всех сервисов
docker compose ps

# Проверить логи
docker compose logs web -f
docker compose logs bot -f
```

## 🌐 Регистрация новой компании

Новые компании регистрируются через публичный API:

1. Перейдите на страницу регистрации: `https://your-domain.com/register`
2. Заполните данные компании:
   - Название автосервиса
   - Email
   - Телефон
   - Токен Telegram бота (полученный от BotFather)
   - Администратор Telegram ID
   - Выберите тарифный план
3. Нажмите "Зарегистрироваться"
4. Оплатите подписку через Юкассу
5. После успешной оплаты:
   - Компания будет создана
   - Tenant схема будет создана
   - Подписка будет активирована
   - Telegram бот будет запущен автоматически

## 📁 Структура проекта

```
autoservice/
├── bot/                         # Telegram боты
│   ├── handlers/                  # Обработчики событий
│   ├── keyboards/                 # Inline клавиатуры
│   ├── middleware/                 # Middleware для проверки подписки
│   ├── bot_manager.py             # Управление всеми ботами
│   ├── super_admin_bot.py         # Бот супер-админа
│   └── main.py                    # Точка входа для всех ботов
├── web/
│   ├── backend/                   # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/              # API endpoints
│   │   │   │   ├── public.py    # Публичный API (регистрация)
│   │   │   │   ├── super_admin.py # API супер-админа
│   │   │   │   ├── bot_manager.py # API управления ботами
│   │   │   │   └── *_tenant.py # Tenant API endpoints
│   │   │   ├── models/            # SQLAlchemy модели
│   │   │   │   └── public_models.py # Public schema модели
│   │   │   ├── schemas/           # Pydantic схемы
│   │   │   ├── services/          # Бизнес логика
│   │   │   │   ├── tenant_service.py # Управление tenant схемами
│   │   │   │   ├── subscription_service.py # Управление подписками
│   │   │   │   └── payment_service.py # Управление платежами
│   │   │   ├── tasks/             # Celery задачи
│   │   │   │   └── subscription_notifications.py # Напоминания
│   │   │   └── config.py          # Конфигурация
│   │   ├── alembic/                # Миграции базы данных
│   │   ├── celeryconfig.py        # Конфигурация Celery
│   │   ├── scripts/                # Скрипты инициализации
│   │   └── Dockerfile              # Docker конфигурация
│   └── frontend/                  # React frontend
│       ├── src/
│       │   ├── pages/            # Страницы приложения
│       │   │   ├── Register.tsx  # Регистрация компании
│       │   │   ├── SuperAdmin*   # Супер-админ панель
│       │   │   └── ...           # Админ панель компании
│       │   ├── api/              # API клиенты
│       │   └── components/        # React компоненты
│       └── Dockerfile              # Docker конфигурация
├── shared/                       # Общий код
│   └── database/                 # Общие модели БД
├── md/                          # Документация по этапам
├── docker-compose.yml              # Docker compose конфигурация
├── .env.example                  # Пример переменных окружения
├── requirements.txt               # Python зависимости
└── README.md                    # Этот файл
```

## 🔧 Команды Docker

### Основные команды
```bash
# Запуск всех сервисов
docker compose up -d

# Остановка всех сервисов
docker compose down

# Пересборка сервисов
docker compose build

# Просмотр логов
docker compose logs web -f
docker compose logs bot -f
docker compose logs celery-worker -f
docker compose logs celery-beat -f

# Статус всех контейнеров
docker compose ps

# Перезапуск конкретного сервиса
docker compose restart web
docker compose restart bot
docker compose restart celery-worker
docker compose restart celery-beat
```

### Команды для работы с базой данных
```bash
# Подключиться к PostgreSQL
docker compose exec postgres psql -U autoservice_user -d autoservice_db

# Применить миграции
docker compose exec web python -m alembic upgrade head

# Откатить миграции
docker compose exec web python -m alembic downgrade -1

# Создать начальные данные
docker compose exec web python scripts/seed.py
```

### Команды для Celery
```bash
# Запустить воркер Celery
docker compose exec celery-worker celery -A celeryconfig.celery_app worker --loglevel=info

# Запустить Celery Beat
docker compose exec celery-beat celery -A celeryconfig.celery_app beat --loglevel=info

# Проверить активные задачи
docker compose exec celery-worker celery -A celeryconfig.celery_app inspect active
```

## 📚 Документация

### Для пользователей (клиентов)
- [USER_GUIDE.md](md/USER_GUIDE.md) - Руководство для клиентов
- [BOT_GUIDE.md](md/BOT_GUIDE.md) - Как пользоваться Telegram ботом

### Для администраторов компаний
- [ADMIN_GUIDE.md](md/ADMIN_GUIDE.md) - Руководство для админов компаний
- [COMPANY_ADMIN_PANEL.md](md/COMPANY_ADMIN_PANEL.md) - Админ панель компании

### Для супер-администраторов
- [SUPER_ADMIN_GUIDE.md](md/SUPER_ADMIN_GUIDE.md) - Руководство для супер-админа
- [SUPER_ADMIN_PANEL.md](md/SUPER_ADMIN_PANEL.md) - Админ панель супер-админа

### Для разработчиков
- [01_PROJECT_OVERVIEW.md](md/01_PROJECT_OVERVIEW.md) - Обзор проекта
- [02_BACKEND_MODELS.md](md/02_BACKEND_MODELS.md) - Модели базы данных
- [03_BACKEND_MULTI_TENANT.md](md/03_BACKEND_MULTI_TENANT.md) - Мульти-тенантность
- [04_BILLING_SUBSCRIPTIONS.md](md/04_BILLING_SUBSCRIPTIONS.md) - Биллинг и подписки
- [05_MULTI_BOTS.md](md/05_MULTI_BOTS.md) - Мульти-боты
- [06_CELERY_TASKS.md](md/06_CELERY_TASKS.md) - Celery задачи
- [07_TELEGRAM_BOT_MULTI_TENANT.md](md/07_TELEGRAM_BOT_MULTI_TENANT.md) - Telegram боты
- [08_FRONTEND_REGISTRATION.md](md/08_FRONTEND_REGISTRATION.md) - Frontend регистрация
- [09_FRONTEND_SUPER_ADMIN.md](md/09_FRONTEND_SUPER_ADMIN.md) - Frontend супер-админ
- [10_FRONTEND_COMPANY_ADMIN.md](md/10_FRONTEND_COMPANY_ADMIN.md) - Frontend админ компания
- [11_TESTING.md](md/11_TESTING.md) - Тестирование

### API документация
- Swagger UI: `https://your-domain.com/docs` - Интерактивная документация API
- ReDoc: `https://your-domain.com/redoc` - Альтернативная документация API

## 📊 Архитектура

### Мульти-тенантность

Проект использует схему мульти-тенантности с изолированием данных на уровне базы данных:

```
┌─────────────────────────────────────────────────┐
│         PostgreSQL Database              │
│                                           │
│  ┌──────────────────────────────────┐        │
│  │      public schema             │        │
│  │   (глобальные данные)          │        │
│  │   - companies                    │        │
│  │   - subscriptions               │        │
│  │   - payments                    │        │
│  │   - plans                       │        │
│  └──────────────────────────────────┘        │
│                                           │
│  ┌──────────────────────────────────┐        │
│  │      tenant_001 schema         │        │
│  │   (данные компании 1)           │        │
│  │   - bookings                     │        │
│  │   - users                        │        │
│  │   - services                     │        │
│  └──────────────────────────────────┘        │
│                                           │
│  ┌──────────────────────────────────┐        │
│  │      tenant_002 schema         │        │
│  │   (данные компании 2)           │        │
│  └──────────────────────────────────┘        │
│                                           │
└───────────────────────────────────────────────┘
```

### Компоненты

```
┌─────────────────────────────────────────────────┐
│        Frontend (React)             │
│                                           │
│  ┌────────────┐  ┌──────────┐  │
│  │ Публичные  │  │ Админ    │  │
│  │ страницы    │  │ панель   │  │
│  │            │  │          │  │
│  │ Регистрация │  │ Dashboard│  │
│  └────────────┘  └──────────┘  │
│         │                │             │
└────────┼────────────────┼─────────────┘
         │                │
         ▼                ▼
┌─────────────────────────────────────────────────┐
│         Backend (FastAPI)            │
│                                           │
│  ┌────────────┐  ┌──────────┐  │
│  │ Public     │  │ Tenant   │  │
│  │ API        │  │ API      │  │
│  │            │  │          │  │
│  │ /public    │  │ /api     │  │
│  │ /webhooks  │  │          │  │
│  └────────────┘  └──────────┘  │
│         │                │             │
└────────┼────────────────┼─────────────┘
         │                │
         ▼                ▼
┌─────────────────────────────────────────────────┐
│         Database (PostgreSQL)       │
└─────────────────────────────────────────────────┘

         │
         ▼
┌─────────────────────────────────────────────────┐
│         Telegram Bots              │
│                                           │
│  ┌────────────┐  ┌──────────┐  │
│  │ Бот        │  │ Супер    │  │
│  │ компании    │  │ админ    │  │
│  │            │  │ бот      │  │
│  │ Запись,    │  │          │  │
│  │ управление  │  │ Мониторинг│  │
│  └────────────┘  └──────────┘  │
└─────────────────────────────────────────────────┘
```

## 🔐 Безопасность

### Аутентификация
- JWT токены для авторизации пользователей
- Хеширование паролей с bcrypt
- Защита от CSRF атак

### Изоляция данных
- Каждый компания имеет отдельную tenant схему
- Middleware для проверки company_id
- Запрет доступа к данным других компаний

### Платежи
- Интеграция с Юкассой
- Webhook для обработки платежей
- Безопасная обработка подписи webhook

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи сервисов:
```bash
docker compose logs web -f --tail 100
docker compose logs bot -f --tail 100
docker compose logs celery-worker -f --tail 100
```

2. Проверьте документацию:
- [USER_GUIDE.md](md/USER_GUIDE.md)
- [ADMIN_GUIDE.md](md/ADMIN_GUIDE.md)
- [SUPER_ADMIN_GUIDE.md](md/SUPER_ADMIN_GUIDE.md)

3. Сообщите об ошибке:
- Создайте issue на GitHub
- Укажите версию проекта
- Прикрепите логи ошибок

## 📝 Лицензия

Этот проект является коммерческим продуктом. Все права защищены.

## 🤝 Участие в разработке

Если вы хотите участвовать в разработке проекта, пожалуйста:

1. Создайте fork проекта на GitHub
2. Создайте feature branch
3. Внесите свои изменения
4. Создайте pull request

---

**AutoService SaaS** - Мульти-тенантная платформа для управления автосервисами

Версия: 2.0  
Автор: AutoService Team  
Дата: 2026
