# SQL Скрипты для AutoService SaaS

## 📋 Обзор

Эта папка содержит SQL скрипты для создания таблиц и заполнения начальными данными для AutoService SaaS платформы.

## 📁 Файлы

| Файл | Описание |
|------|----------|
| `create_multi_tenant_tables.sql` | Создание всех таблиц мульти-тенантной архитектуры |
| `seed_data.sql` | Заполнение БД начальными данными (тарифные планы, супер-администратор) |

## 🚀 Применение SQL скриптов

### Вариант 1: Внутри Docker контейнера

```bash
# 1. Подключитесь к контейнеру PostgreSQL
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# 2. Примените скрипт создания таблиц
\i /sql/create_multi_tenant_tables.sql

# 3. Примените скрипт начальных данных
\i /sql/seed_data.sql

# 4. Выйдите из PostgreSQL
\q
```

### Вариант 2: Из внешней консоли

```bash
# Применить скрипт создания таблиц
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql

# Применить скрипт начальных данных
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql
```

### Вариант 3: Локальное подключение (без Docker)

```bash
# Если PostgreSQL установлен локально
psql -h localhost -p 5433 -U autoservice_user -d autoservice_db -f sql/create_multi_tenant_tables.sql

psql -h localhost -p 5433 -U autoservice_user -d autoservice_db -f sql/seed_data.sql
```

### Вариант 4: Через psql с параметрами

```bash
# Создание таблиц
psql postgresql://autoservice_user:your_password@localhost:5433/autoservice_db -f sql/create_multi_tenant_tables.sql

# Начальные данные
psql postgresql://autoservice_user:your_password@localhost:5433/autoservice_db -f sql/seed_data.sql
```

## 🗂️ Структура БД после применения скриптов

### Схемы

```
public (глобальные данные)
├── plans (тарифные планы)
├── companies (компании - автосервисы)
├── subscriptions (подписки)
├── payments (платежи)
└── super_admins (супер-администраторы)

tenant_001 (первая компания)
├── users
├── clients
├── masters
├── services
├── bookings
├── posts
├── promocodes
├── promotions
├── notifications
├── broadcasts
├── settings
├── booking_history
├── client_history
├── timeslots
├── blocked_slots
└── master_services

tenant_002 (вторая компания)
└── ... (те же таблицы, что и tenant_001)
```

### ENUM Types

- `subscription_status`: `pending`, `active`, `suspended`, `cancelled`, `expired`
- `payment_status`: `pending`, `processing`, `succeeded`, `cancelled`, `failed`, `refunded`

## ✅ Проверка

### Проверка созданных таблиц

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# Список схем
\dn

# Таблицы в public схеме
\dt public.*

# Структура таблицы
\d plans
\d companies
\d subscriptions
\d payments
\d super_admins

# Выйти
\q
```

### Проверка начальных данных

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# Тарифные планы
SELECT * FROM public.plans ORDER BY display_order;

# Супер-администраторы
SELECT id, username, email, is_active FROM public.super_admins;

# Типы данных
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'subscription_status'::regtype ORDER BY enumsortorder;
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'payment_status'::regtype ORDER BY enumsortorder;

# Выйти
\q
```

### Проверка через API

```bash
# Получить тарифные планы
curl http://localhost:8000/api/public/plans

# Проверить health
curl http://localhost:8000/api/health
```

## 🔄 Откат изменений

### Удаление таблиц (осторожно!)

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

-- Удалить в обратном порядке из-за foreign keys
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS super_admins CASCADE;

-- Удалить типы
DROP TYPE IF EXISTS payment_status CASCADE;
DROP TYPE IF EXISTS subscription_status CASCADE;

-- Выйти
\q
```

### Полная очистка БД

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

-- Удалить все таблицы в public схеме
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Гранты
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO autoservice_user;

-- Выйти
\q

-- Применить скрипты заново
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql
```

## 📊 Статистика

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

-- Количество тарифных планов
SELECT COUNT(*) as plans_count FROM plans;

-- Количество компаний
SELECT COUNT(*) as companies_count FROM companies;

-- Количество подписок
SELECT COUNT(*) as subscriptions_count FROM subscriptions;

-- Количество платежей
SELECT COUNT(*) as payments_count FROM payments;

-- Количество супер-администраторов
SELECT COUNT(*) as super_admins_count FROM super_admins;

-- Статистика по платежам
SELECT status, COUNT(*) as count FROM payments GROUP BY status;

-- Статистика по подпискам
SELECT status, COUNT(*) as count FROM subscriptions GROUP BY status;

-- Выйти
\q
```

## 🔧 Изменение пароля супер-администратора

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

-- Обновить пароль (замените 'new_password_hash' на хеш)
UPDATE super_admins 
SET password_hash = '$2b$12$...new_hash...' 
WHERE username = 'admin';

-- Проверить изменения
SELECT username, email, is_active FROM super_admins;

-- Выйти
\q
```

Для генерации нового хеша пароля:

```bash
python -c "
from passlib.context import CryptContext
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd.hash('your_new_password'))
"
```

## 📝 Создание новых тарифных планов

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

-- Добавить новый тарифный план
INSERT INTO plans (
    name, 
    description, 
    price_monthly, 
    price_yearly, 
    max_bookings_per_month, 
    max_users, 
    max_masters, 
    max_posts, 
    max_promotions, 
    display_order, 
    is_active
) VALUES (
    'Custom',
    'Индивидуальный тариф',
    19990.00,
    199900.00,
    2000,
    200,
    100,
    200,
    100,
    4,
    TRUE
);

-- Проверить добавление
SELECT * FROM plans ORDER BY display_order;

-- Выйти
\q
```

## 🐛 Устранение проблем

### Ошибка: "relation already exists"

Таблицы уже созданы. Проверьте существующие таблицы:

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*
```

Если таблицы существуют, пропустите создание или удалите их перед повторным созданием.

### Ошибка: "type already exists"

Типы данных уже созданы. Это нормально, скрипты используют `IF NOT EXISTS` для типов.

### Ошибка: "permission denied"

Убедитесь, что пользователь `autoservice_user` имеет права на создание таблиц:

```bash
docker exec -it autoservice_postgres psql -U postgres -d autoservice_db

GRANT ALL PRIVILEGES ON SCHEMA public TO autoservice_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO autoservice_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO autoservice_user;
```

### Ошибка: "could not connect to server"

Проверьте, что контейнер PostgreSQL запущен:

```bash
docker ps | grep postgres

# Или
docker-compose ps
```

Если контейнер не запущен:

```bash
docker-compose up -d postgres
```

## 📚 Полезные команды

```bash
# Просмотр логов PostgreSQL
docker logs -f autoservice_postgres

# Перезапуск PostgreSQL
docker-compose restart postgres

# Подключение к PostgreSQL
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# Экспорт данных
docker exec autoservice_postgres pg_dump -U autoservice_user autoservice_db > backup.sql

# Импорт данных
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < backup.sql

# Размер базы данных
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db -c "SELECT pg_size_pretty(pg_database_size('autoservice_db'));"

-- Размер конкретной таблицы
SELECT pg_size_pretty(pg_total_relation_size('companies'));
```

## 🎯 После применения скриптов

1. ✅ Проверьте, что все таблицы созданы (`\dt public.*`)
2. ✅ Проверьте, что начальные данные загружены
3. ✅ Проверьте работу API (`curl http://localhost:8000/api/health`)
4. ✅ Протестируйте страницу регистрации (`http://localhost:3000/register`)
5. ✅ Войдите в админ-панель под супер-администратором

## 📖 Документация

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose](https://docs.docker.com/compose/)
- [SQL Reference](https://www.postgresql.org/docs/current/sql.html)

---

**Для автоматического применения миграций используйте Alembic:**
```bash
cd web/backend
python scripts/migrate.py
python scripts/seed.py
```

**Для ручного применения используйте эти SQL скрипты.**

