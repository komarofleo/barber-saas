# 📊 Сводка по миграциям БД для AutoService SaaS

## ✅ Созданные файлы

### Python скрипты (рекомендуемый способ)

| Файл | Описание | Место |
|------|----------|-------|
| `migrate.py` | Применение миграций через Alembic | `web/backend/scripts/` |
| `seed.py` | Заполнение БД начальными данными | `web/backend/scripts/` |
| `check_migrations.py` | Проверка состояния миграций | `web/backend/scripts/` |

### SQL скрипты (альтернативный способ)

| Файл | Описание | Место |
|------|----------|-------|
| `create_multi_tenant_tables.sql` | Создание всех таблиц | `sql/` |
| `seed_data.sql` | Начальные данные (планы, админ) | `sql/` |
| `README.md` | Инструкции по применению SQL | `sql/` |

### Документация

| Файл | Описание | Место |
|------|----------|-------|
| `MIGRATION_GUIDE.md` | Полное руководство по миграциям | Корень проекта |
| `ENV_SETUP_GUIDE.md` | Настройка переменных окружения | Корень проекта |

### Миграции Alembic

| Файл | Описание | Место |
|------|----------|-------|
| `001_create_multi_tenant_tables.py` | Первая миграция для public схемы | `web/backend/alembic/versions/` |

## 🚀 Быстрый старт

### Способ 1: Через Python скрипты (рекомендуется)

```bash
# 1. Настройте .env файл
cp .env.example .env
# Отредактируйте .env с вашими настройками

# 2. Примените миграции
cd web/backend
python scripts/migrate.py

# 3. Заполните БД начальными данными
python scripts/seed.py

# 4. Проверьте состояние миграций
python scripts/check_migrations.py
```

### Способ 2: Через SQL скрипты (если Alembic не работает)

```bash
# 1. Примените скрипт создания таблиц
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql

# 2. Примените скрипт начальных данных
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql

# 3. Проверьте созданные таблицы
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*
\q
```

### Способ 3: Через Alembic CLI

```bash
cd web/backend

# Применить все миграции
alembic upgrade head

# Посмотреть текущую версию
alembic current

# Посмотреть историю миграций
alembic history
```

## 📋 Что создается

### Таблицы (public схема)

1. **plans** - Тарифные планы подписки
   - Starter: 2 990 ₽/мес, 50 записей/мес
   - Pro: 5 990 ₽/мес, 200 записей/мес
   - Business: 11 990 ₽/мес, 1000 записей/мес

2. **companies** - Автосервисы (клиенты)
   - Настройки компании
   - Информация о подписке
   - Данные Telegram бота

3. **subscriptions** - Подписки компаний
   - Дата начала и конца
   - Статус подписки
   - Привязка к тарифному плану

4. **payments** - Платежи через Юкассу
   - Данные от Юкассы
   - Статус платежа
   - Webhook данные

5. **super_admins** - Супер-администраторы
   - Данные для входа
   - Права доступа

### ENUM Types

- `subscription_status`: pending, active, suspended, cancelled, expired
- `payment_status`: pending, processing, succeeded, cancelled, failed, refunded

### Индексы

Все основные поля проиндексированы для быстрого поиска:
- email, name (companies)
- subscription_status, plan_id (companies, subscriptions)
- status, yookassa_payment_id (payments)
- username, email (super_admins)

## 🔄 Порядок выполнения

### 1. Подготовка окружения

```bash
# Проверьте наличие Docker контейнеров
docker ps

# Запустите контейнеры если нужно
docker-compose up -d postgres web

# Подождите пока PostgreSQL будет готов (около 10 секунд)
```

### 2. Настройка переменных окружения

```bash
# Скопируйте пример .env
cp .env.example .env

# Отредактируйте .env
nano .env

# Минимальные настройки:
# DB_PASSWORD=your_secure_password
# BOT_TOKEN=your_telegram_bot_token
# WEB_SECRET_KEY=your_secret_key_min_32_chars
# YOOKASSA_SHOP_ID=your_shop_id
# YOOKASSA_SECRET_KEY=your_secret_key
```

### 3. Применение миграций

**Выберите один из способов:**

#### Способ A: Python скрипты (рекомендуется)
```bash
cd web/backend
python scripts/migrate.py
python scripts/seed.py
```

#### Способ B: SQL скрипты (резервный)
```bash
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql
```

#### Способ C: Alembic CLI
```bash
cd web/backend
alembic upgrade head
```

### 4. Проверка результатов

```bash
# Проверьте таблицы
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*
SELECT COUNT(*) FROM plans;
SELECT COUNT(*) FROM super_admins;
\q

# Проверьте через API
curl http://localhost:8000/api/health
curl http://localhost:8000/api/public/plans
```

## ✅ Проверка успешности

После применения миграций убедитесь в следующем:

### 1. Таблицы созданы

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*

Ожидается:
- plans
- companies
- subscriptions
- payments
- super_admins
```

### 2. Начальные данные загружены

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# Тарифные планы (должно быть 3)
SELECT * FROM plans;

# Супер-администратор (должен быть 1)
SELECT * FROM super_admins;
```

### 3. API отвечает

```bash
# Health check
curl http://localhost:8000/api/health

# Получить планы
curl http://localhost:8000/api/public/plans
```

### 4. Frontend работает

```bash
# Откройте в браузере
http://localhost:3000
http://localhost:3000/register
```

## 🐛 Устранение проблем

### Проблема: "alembic: command not found"

**Решение:** Используйте Python скрипты вместо Alembic CLI

```bash
cd web/backend
python scripts/migrate.py
```

### Проблема: "docker: command not found"

**Решение:** Применяйте SQL скрипты напрямую через psql

```bash
psql -h localhost -p 5433 -U autoservice_user -d autoservice_db -f sql/create_multi_tenant_tables.sql
psql -h localhost -p 5433 -U autoservice_user -d autoservice_db -f sql/seed_data.sql
```

### Проблема: "relation already exists"

**Решение:** Таблицы уже созданы, проверьте их

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*
```

Если таблицы существуют, пропустите создание или удалите их:

```sql
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS super_admins CASCADE;
```

### Проблема: "No module named 'app'"

**Решение:** Установите PYTHONPATH

```bash
cd web/backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts/migrate.py
```

### Проблема: "could not connect to server"

**Решение:** Проверьте контейнер PostgreSQL

```bash
docker ps | grep postgres

# Если не запущен
docker-compose up -d postgres

# Проверьте логи
docker logs autoservice_postgres
```

## 📝 Данные для входа (после seed)

### Супер-администратор

- **Username:** `admin`
- **Email:** `admin@autoservice.com`
- **Password:** `admin123`

⚠️ **Важно:** Обязательно измените пароль после первого входа!

### Тарифные планы

| ID | Название | Цена/мес | Цена/год | Записи/мес |
|----|----------|-----------|-----------|-------------|
| 1 | Starter | 2 990 ₽ | 29 900 ₽ | 50 |
| 2 | Pro | 5 990 ₽ | 59 900 ₽ | 200 |
| 3 | Business | 11 990 ₽ | 119 900 ₽ | 1000 |

## 🎯 Следующие шаги

После успешного применения миграций:

1. ✅ **Запустите все сервисы**
   ```bash
   docker-compose up -d
   ```

2. ✅ **Проверьте работу API**
   ```bash
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/public/plans
   ```

3. ✅ **Откройте Frontend**
   - Админ-панель: `http://localhost:3000`
   - Страница регистрации: `http://localhost:3000/register`

4. ✅ **Войдите как супер-администратор**
   - Используйте данные выше
   - Измените пароль после первого входа

5. ✅ **Протестируйте регистрацию нового клиента**
   - Перейдите на страницу регистрации
   - Заполните форму
   - Проверьте создание платежа в Юкассу

6. ✅ **Проверьте webhook обработку**
   - После успешной оплаты в Юкассу
   - Проверьте создание компании
   - Проверьте создание tenant схемы

7. ✅ **Запустите боты**
   - BotManager автоматически запустит боты для активных компаний
   - Проверьте работоспособность ботов

## 📚 Дополнительная документация

- [Полное руководство по миграциям](MIGRATION_GUIDE.md)
- [Настройка переменных окружения](ENV_SETUP_GUIDE.md)
- [SQL скрипты README](sql/README.md)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🔄 Сравнение способов применения миграций

| Способ | Преимущества | Недостатки | Рекомендуется |
|--------|--------------|-------------|---------------|
| **Python скрипты** | Простой, проверенный, автоматический | Требует Python | ✅ Да |
| **SQL скрипты** | Прямой контроль, отладка | Ручной процесс | ⚠️ Резервный |
| **Alembic CLI** | Стандартный, гибкий | Может не работать в некоторых средах | ✅ Да |

## 📊 Статус миграций

| Компонент | Статус | Описание |
|-----------|--------|----------|
| Модели | ✅ Созданы | Company, Plan, Subscription, Payment, SuperAdmin |
| Pydantic схемы | ✅ Созданы | Все схемы для API |
| Миграция Alembic | ✅ Создана | `001_create_multi_tenant_tables.py` |
| Python скрипты | ✅ Созданы | migrate.py, seed.py, check_migrations.py |
| SQL скрипты | ✅ Созданы | create_multi_tenant_tables.sql, seed_data.sql |
| Документация | ✅ Создана | MIGRATION_GUIDE.md, ENV_SETUP_GUIDE.md |

## 🎉 Итого

**Все готово для применения миграций!**

Выберите один из способов:
1. **Python скрипты (рекомендуется)**: `python scripts/migrate.py && python scripts/seed.py`
2. **SQL скрипты**: `psql ... < sql/create_multi_tenant_tables.sql && ... < sql/seed_data.sql`
3. **Alembic CLI**: `alembic upgrade head`

После применения миграций следуйте инструкциям в разделе "Следующие шаги".

---

**Удачи! 🚀**

