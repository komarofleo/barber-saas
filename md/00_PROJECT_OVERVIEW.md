# 🎯 Обзор проекта: AutoService SaaS

**Версия:** 2.0 (Multi-Tenant)  
**Дата:** 06.01.2026  
**Статус:** В разработке

---

## 📋 Содержание

1. [Назначение проекта](#назначение-проекта)
2. [Архитектура](#архитектура)
3. [Технологический стек](#технологический-стек)
4. [Функциональные требования](#функциональные-требования)
5. [Структура базы данных](#структура-базы-данных)
6. [Структура проекта](#структура-проекта)
7. [План реализации](#план-реализации)
8. [Критерии успеха](#критерии-успеха)

---

## 🎯 Назначение проекта

**AutoService SaaS** - облачная платформа для управления автосервисами с возможностью записи клиентов через Telegram-бот и веб-админ панель.

### Ключевые особенности

- **Мульти-тенантная архитектура** - одна платформа обслуживает множество автосервисов
- **Полная изоляция данных** - каждый клиент (автосервис) имеет отдельную схему БД
- **Отдельные Telegram боты** - каждый клиент получает своего бота
- **Система подписок** - оплата через Юкассу, автоматическое продление
- **Блокировка только записи** - при неоплате данные доступны, но запись отключена

---

## 🏗️ Архитектура

### Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    Пользователи                            │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ Клиент 1     │ Клиент 2     │ Клиент 3     │ ...          │
│ (Автосервис) │ (Автосервис) │ (Автосервис) │              │
│              │              │              │              │
│ @auto_1_bot  │ @auto_2_bot  │ @auto_3_bot  │ ...          │
└──────┬───────┴──────┬───────┴──────┬───────┴──────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
              ┌───────▼────────┐
              │  Telegram API  │
              └───────┬────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
┌──────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│ Bot 1      │ │ Bot 2      │ │ Bot 3     │
│ (process)  │ │ (process)  │ │ (process) │
└──────┬─────┘ └─────┬─────┘ └─────┬─────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
              ┌───────▼───────────────┐
              │  Main Backend         │
              │  (Routing + Billing)  │
              └───────┬───────────────┘
                      │
┌─────────────────────┼─────────────────────┐
│                     │                     │
▼                     ▼                     ▼
┌─────────┐      ┌─────────┐      ┌─────────┐
│ Schema 1│      │ Schema 2│      │ Schema 3│
│ tenant_1│      │ tenant_2│      │ tenant_3│
│ (данные)│      │ (данные)│      │ (данные)│
└─────────┘      └─────────┘      └─────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
              ┌───────▼─────────┐
              │  PostgreSQL DB  │
              └─────────────────┘
```

### Компоненты системы

#### 1. Telegram Bot (Multi-Bot)
- Несколько ботов для разных компаний
- Общая кодовая база
- Динамическая загрузка конфигурации
- Проверка подписки перед созданием записи

#### 2. Backend API
- Публичные API (регистрация)
- API для супер-админа
- API для обычных клиентов
- Middleware для проверки подписки
- Интеграция с Юкассой

#### 3. Frontend
- Публичная страница регистрации
- Админ-панель супер-админа
- Админ-панель обычных клиентов
- Обновленные существующие страницы

#### 4. Database
- Схема `public` - общие данные (компании, подписки, платежи)
- Схемы `tenant_001`, `tenant_002`, ... - данные клиентов
- Полная изоляция данных

#### 5. Celery Tasks
- Напоминания об оплате
- Проверка просроченных подписок
- Обработка webhook от Юкассы
- Отправка лист-нарядов мастерам

---

## 🛠️ Технологический стек

### Backend
- **Python 3.11+**
- **FastAPI** - веб-фреймворк
- **SQLAlchemy 2.0** (async) - ORM
- **PostgreSQL 15** - база данных
- **Redis 7** - кэш и брокер сообщений
- **Celery + Celery Beat** - фоновые задачи
- **Alembic** - миграции БД
- **aiogram 3.x** - Telegram боты
- **Pydantic** - валидация данных
- **python-jose** - JWT аутентификация
- **aiohttp** - HTTP клиент для API Telegram и Юкассы

### Frontend
- **React 18 + TypeScript**
- **Vite** - сборщик
- **React Router v6** - маршрутизация
- **Recharts** - графики
- **axios** - HTTP клиент
- **Material-UI** - UI компоненты (опционально)

### DevOps
- **Docker + Docker Compose** - контейнеризация
- **Nginx** - веб-сервер
- **PostgreSQL 15** - база данных
- **Redis 7** - кэш и брокер

### Интеграции
- **Telegram Bot API** - работа с ботами
- **Юкасса (YooKassa)** - оплата картой
- **Email/SMS** - уведомления (для реализации)

---

## 📋 Функциональные требования

### 1. Публичная регистрация нового клиента

**Пользовательская история:**
- Владелец автосервиса переходит на публичную страницу
- Заполняет: название, email, телефон
- Вводит токен созданного через @BotFather бота
- Выбирает тарифный план
- Перенаправляется на оплату через Юкассу
- После оплаты получает доступ

**Требования:**
- Публичная страница (без авторизации)
- Валидация токена через Telegram API
- Уникальный код компании (авто-генерация или вручную)
- Интеграция с Юкассой
- Автоматическое создание схемы БД после оплаты
- Email/SMS уведомление с доступом

**API endpoints:**
- `POST /api/public/validate-bot-token`
- `POST /api/public/companies/register`
- `POST /api/public/payments/create`
- `POST /api/payments/yookassa/webhook`

**Frontend страницы:**
- `PublicRegistration.tsx`
- `PlanSelection.tsx`
- `BotTokenInput.tsx`
- `PaymentConfirmation.tsx`

---

### 2. Админ-панель супер-админа (Billing)

**Пользовательская история:**
- Супер-админ авторизуется
- Видит общую статистику по всем клиентам
- Просматривает список компаний с фильтрами
- Управляет подписками и платежами
- Блокирует/разблокирует клиентов

**Требования:**
- Дашборд с виджетами (выручка, клиенты, подписки)
- Графики (выручка по дням, клиенты по месяцам)
- Список компаний (фильтры: статус, тариф, дата)
- Детали компании (подписка, платежи, статистика)
- Страница биллинга с платежами
- Блокировка (только запись или полностью)
- Экспорт данных в Excel

**API endpoints:**
- `GET /api/super-admin/dashboard/stats`
- `GET /api/super-admin/companies`
- `GET /api/super-admin/companies/{id}`
- `PATCH /api/super-admin/companies/{id}/block`
- `GET /api/super-admin/billing/stats`
- `GET /api/super-admin/billing/payments`
- `POST /api/super-admin/billing/export`

**Frontend страницы:**
- `SuperAdminDashboard.tsx`
- `SuperAdminCompanies.tsx`
- `SuperAdminCompanyDetails.tsx`
- `SuperAdminBilling.tsx`

---

### 3. Мульти-тенантная архитектура (Backend)

**Требования:**
- Одна БД с несколькими схемами
- Схема `public` - общие данные
- Схемы `tenant_001`, `tenant_002`, ... - данные клиентов
- Динамическое подключение к нужной схеме
- Полная изоляция данных
- Поддержка миграций для новых схем

**Технические требования:**
- `SessionManager` для работы с несколькими схемами
- Middleware для проверки подписки
- CRUD функции с параметром `company_id`
- Функции создания/удаления схем
- Автоматическое применение миграций в схемы

---

### 4. Мульти-бот система (Telegram)

**Требования:**
- Несколько ботов для разных компаний
- Общая кодовая база
- Динамическая загрузка конфигурации
- Каждый бот работает со своей схемой
- Проверка подписки перед созданием записи
- Сообщения об истекшей подписке

**Технические требования:**
- Переписать `bot/main.py` для запуска нескольких ботов
- Контекст (company_id, schema_name) в диспетчере
- Tenant-сессии для работы с правильной схемой
- Проверка `can_create_bookings` в хендлерах
- Рестарт бота при регистрации нового клиента

---

### 5. Система подписок и оплат

**Требования:**
- Три тарифных плана (Starter 2990₽, Pro 4990₽, Business 9990₽)
- Подписка на 1 месяц с автопродлением
- Блокировка только записи при неоплате
- История всех платежей

**Интеграция с Юкассой:**
- Создание платежа при регистрации
- Обработка webhook
- Автоматическое создание подписки после оплаты
- Генерация чеков
- Обработка возвратов

**Напоминания (Celery):**
- За 7 дней до окончания
- За 3 дня до окончания
- В день окончания
- На следующий день (блокировка записи)
- Через 7 дней (полная блокировка)

---

### 6. Миграция существующего клиента

**Требования:**
- Перенос данных текущего клиента в `tenant_001`
- Создание записи компании в схеме `public`
- Создание подписки
- Сохранение работоспособности системы
- Возможность отката миграции

**План миграции:**
1. Создать новые таблицы в схеме `public`
2. Создать запись компании для текущего клиента
3. Создать схему `tenant_001`
4. Перенести все таблицы из `public` в `tenant_001`
5. Удалить старые таблицы из `public`
6. Проверить работу системы

---

## 🗄️ Структура базы данных

### Схема `public` (общие данные)

#### Таблица: companies
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    telegram_bot_token VARCHAR(500) UNIQUE,
    telegram_bot_username VARCHAR(255),
    webhook_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    subscription_status VARCHAR(50) DEFAULT 'trial',
    subscription_end_date DATE,
    max_users INTEGER,
    max_masters INTEGER,
    max_posts INTEGER,
    can_create_bookings BOOLEAN DEFAULT TRUE,
    features JSONB DEFAULT '{}',
    
    INDEX idx_companies_code (code),
    INDEX idx_companies_subscription_status (subscription_status)
);
```

#### Таблица: plans
```sql
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    price_monthly DECIMAL(10, 2) NOT NULL,
    max_users INTEGER NOT NULL,
    max_masters INTEGER NOT NULL,
    max_posts INTEGER NOT NULL,
    max_bookings_per_day INTEGER NOT NULL,
    features JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_plans_active (is_active)
);
```

**Инициализация планов:**
- Starter: 2990₽, 3 мастера, 2 поста, 20 записей/день
- Pro: 4990₽, 10 мастеров, 5 постов, 50 записей/день
- Business: 9990₽, безлимит

#### Таблица: subscriptions
```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES plans(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    auto_renewal BOOLEAN DEFAULT FALSE,
    payment_method VARCHAR(50),
    yookassa_payment_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_subscriptions_company (company_id),
    INDEX idx_subscriptions_status (status),
    INDEX idx_subscriptions_end_date (end_date)
);
```

#### Таблица: payments
```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    payment_date TIMESTAMP,
    payment_method VARCHAR(50),
    yookassa_payment_id VARCHAR(255) UNIQUE,
    yookassa_payment_status VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    receipt_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_payments_company (company_id),
    INDEX idx_payments_status (status),
    INDEX idx_payments_payment_date (payment_date)
);
```

#### Таблица: super_admins
```sql
CREATE TABLE super_admins (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_super_admins_telegram (telegram_id)
);
```

### Схемы `tenant_001`, `tenant_002`, ... (данные клиентов)

Каждая схема содержит одинаковый набор таблиц:

- users
- clients
- bookings
- services
- masters
- posts
- blocked_slots
- promocodes
- promotions
- notifications
- broadcasts
- client_history
- booking_history
- settings
- timeslots
- master_services

---

## 📁 Структура проекта

### Backend

```
web/backend/app/
├── api/
│   ├── public.py                    # Публичные API (регистрация)
│   ├── companies.py                 # Управление компаниями
│   ├── billing.py                   # Биллинг и платежи
│   └── super_admin.py               # API для супер-админа
│
├── models/
│   ├── company.py                   # Модель Company
│   ├── plan.py                      # Модель Plan
│   ├── subscription.py               # Модель Subscription
│   ├── payment.py                   # Модель Payment
│   └── super_admin.py               # Модель SuperAdmin
│
├── schemas/
│   ├── company.py                   # Pydantic схемы для компании
│   ├── plan.py                      # Схемы для тарифов
│   ├── subscription.py               # Схемы для подписок
│   ├── payment.py                   # Схемы для платежей
│   └── super_admin.py               # Схемы для супер-админа
│
├── services/
│   ├── company_service.py            # Бизнес-логика компаний
│   ├── subscription_service.py       # Бизнес-логика подписок
│   ├── payment_service.py           # Бизнес-логика платежей
│   ├── yookassa_service.py          # Интеграция с Юкассой
│   └── tenant_service.py            # Управление схемами
│
├── middleware/
│   ├── subscription_middleware.py    # Проверка подписки
│   └── company_middleware.py       # Определение компании
│
└── tasks/
    ├── subscription_tasks.py         # Задачи подписок
    └── payment_tasks.py            # Задачи платежей
```

### Frontend

```
web/frontend/src/
├── pages/
│   ├── PublicRegistration.tsx       # Публичная регистрация
│   ├── PlanSelection.tsx            # Выбор тарифа
│   ├── PaymentConfirmation.tsx      # Подтверждение оплаты
│   ├── SuperAdminDashboard.tsx      # Дашборд супера
│   ├── SuperAdminCompanies.tsx      # Список компаний
│   ├── SuperAdminCompanyDetails.tsx # Детали компании
│   └── SuperAdminBilling.tsx       # Биллинг
│
├── components/
│   ├── PlanCard.tsx                # Карточка тарифа
│   ├── CompanyTable.tsx             # Таблица компаний
│   ├── PaymentTable.tsx             # Таблица платежей
│   ├── BotTokenInput.tsx            # Ввод токена бота
│   └── BillingStats.tsx            # Статистика биллинга
│
└── api/
    ├── publicApi.ts                 # Публичные API
    ├── companyApi.ts               # API компаний
    └── billingApi.ts               # API биллинга
```

### Scripts

```
scripts/
├── migrate_to_multi_tenant.py      # Миграция данных
├── create_tenant_schema.py         # Создание схемы
├── init_plans.py                   # Инициализация планов
└── init_super_admin.py             # Создание супер-админа
```

---

## 📋 План реализации

| Этап | Название | Дней | Статус | Описание |
|------|---------|------|--------|----------|
| 0 | Обзор проекта | - | ✅ | Этот документ |
| 1 | Подготовка и миграция | 2-3 | ⏳ | Перенос данных текущего клиента |
| 2 | Backend модели | 2-3 | ⏳ | Models и схемы |
| 3 | Backend мульти-тенантность | 3-4 | ⏳ | SessionManager, TenantService |
| 4 | Backend публичные API | 2 | ⏳ | Регистрация, Юкасса |
| 5 | Backend API супера | 2 | ⏳ | Управление компаниями |
| 6 | Celery задачи | 2 | ⏳ | Напоминания |
| 7 | Bot изменения | 3-4 | ⏳ | Мульти-боты |
| 8 | Frontend регистрация | 2-3 | ⏳ | Публичная страница |
| 9 | Frontend админ супера | 3-4 | ⏳ | Управление и биллинг |
| 10 | Frontend обновление | 2-3 | ⏳ | Обновить существующее |
| 11 | Тестирование | 3-4 | ⏳ | Полное тестирование |
| 12 | Деплой | 1-2 | ⏳ | На сервер |
| 13 | Документация | 1 | ⏳ | Инструкции |

**Общий срок:** 28-39 дней (4-6 недель)

---

## ✅ Критерии успеха

### Функциональные критерии

- [ ] Публичная регистрация нового клиента работает
- [ ] Оплата через Юкассу работает
- [ ] Автоматическое создание схемы БД работает
- [ ] Каждый клиент имеет своего бота
- [ ] Данные клиентов полностью изолированы
- [ ] Система подписок работает (напоминания, блокировка)
- [ ] Блокируется только создание записи при неоплате
- [ ] Админ-панель супера работает
- [ ] Статистика по платежам работает
- [ ] Миграция существующего клиента успешна

### Технические критерии

- [ ] Все API endpoints работают корректно
- [ ] Frontend проходит все тесты
- [ ] Backend проходит все тесты
- [ ] Bot работает для нескольких компаний
- [ ] Celery задачи выполняются корректно
- [ ] Миграции Alembic работают
- [ ] Нет утечек памяти
- [ ] Производительность приемлемая (< 500ms на запрос)

### Бизнес критерии

- [ ] Новый клиент может зарегистрироваться за < 5 минут
- [ ] Оплата происходит успешно
- [ ] Подписки продлеваются автоматически
- [ ] Супер-админ видит всю статистику
- [ ] Напоминания об оплате приходят вовремя

---

## 📞 Поддержка и вопросы

### Техническая поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs -f`
2. Обратитесь к документации в папке `md/`
3. Проверьте конфигурацию: `docker compose config`

### Часто задаваемые вопросы

**Q: Можно ли изменить тарифный план?**  
A: Да, можно изменить тариф в любое время через админ-панель супер-админа.

**Q: Что происходит при неоплате?**  
A: Блокируется только создание записей. Просмотр данных остается доступным.

**Q: Можно ли восстановить данные после удаления?**  
A: При удалении компании удаляются только данные этой схемы. Бэкапы создаются ежедневно.

**Q: Как работает изоляция данных?**  
A: Каждый клиент имеет отдельную схему БД. Запросы идут только в свою схему.

---

**Версия:** 2.0  
**Дата:** 06.01.2026  
**Автор:** Claude (Anthropic)

