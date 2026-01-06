# Применение миграций на сервере

## 🚀 Быстрый старт

### Способ 1: Через SSH скрипт (рекомендуется)

```bash
# 1. Сделайте скрипт исполняемым
chmod +x deploy/apply_migrations_remote.sh

# 2. Обновите конфигурацию в скрипте
nano deploy/apply_migrations_remote.sh

# Измените:
# SERVER_USER="your_username" -> ваш логин на сервере
# SERVER_HOST="your_server.com" -> IP или домен сервера
# SERVER_PATH="/path/to/avtoservis" -> путь к проекту на сервере

# 3. Запустите скрипт
./deploy/apply_migrations_remote.sh
```

### Способ 2: Вручную через SSH

```bash
# 1. Подключитесь к серверу
ssh your_username@your_server.com

# 2. Перейдите в директорию проекта
cd /path/to/avtoservis

# 3. Примените миграции через Python скрипты
cd web/backend
python3 scripts/migrate.py

# 4. Заполните БД начальными данными
python3 scripts/seed.py

# 5. Проверьте результат
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c '\dt public.*'
```

### Способ 3: Через Docker и SQL скрипты

```bash
# 1. Подключитесь к серверу
ssh your_username@your_server.com

# 2. Перейдите в директорию проекта
cd /path/to/avtoservis

# 3. Примените SQL скрипты
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/create_multi_tenant_tables.sql

# 4. Примените начальные данные
docker exec -i autoservice_postgres psql -U autoservice_user -d autoservice_db < sql/seed_data.sql
```

### Способ 4: Через psql напрямую

```bash
# 1. Подключитесь к серверу
ssh your_username@your_server.com

# 2. Подключитесь к PostgreSQL напрямую
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# 3. Примените SQL скрипты
\i sql/create_multi_tenant_tables.sql
\i sql/seed_data.sql

# 4. Проверьте результат
\dt public.*
SELECT * FROM plans;
SELECT * FROM super_admins;

# 5. Выйдите
\q
```

## 📋 Проверка результата

### Проверка таблиц

```bash
# Подключитесь к PostgreSQL
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db

# Проверьте созданные таблицы
\dt public.*

# Ожидается:
# - plans
# - companies
# - subscriptions
# - payments
# - super_admins

# Выйдите
\q
```

### Проверка начальных данных

```bash
# Тарифные планы
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT id, name, price_monthly, max_bookings_per_month FROM plans;'

# Супер-администратор
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c 'SELECT username, email, is_active FROM super_admins;'
```

### Проверка через API

```bash
# Health check
curl http://your_server.com:8000/api/health

# Получить тарифные планы
curl http://your_server.com:8000/api/public/plans
```

## 🔧 Устранение проблем

### Проблема: "No module named 'app'"

**Решение:** Установите PYTHONPATH

```bash
cd /path/to/avtoservis/web/backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 scripts/migrate.py
```

### Проблема: "alembic: command not found"

**Решение:** Используйте Python скрипты вместо Alembic CLI

```bash
python3 scripts/migrate.py
```

### Проблема: "relation already exists"

**Решение:** Таблицы уже созданы, проверьте их

```bash
docker exec -it autoservice_postgres psql -U autoservice_user -d autoservice_db
\dt public.*
```

Если таблицы существуют и нужно пересоздать:

```sql
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS super_admins CASCADE;
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

### Проблема: "permission denied for table"

**Решение:** Проверьте права пользователя

```bash
docker exec -it autoservice_postgres psql -U postgres -d autoservice_db

GRANT ALL PRIVILEGES ON SCHEMA public TO autoservice_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO autoservice_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO autoservice_user;
```

## 📊 Статистика после применения миграций

```bash
# Количество таблиц
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"

# Количество тарифных планов
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c "SELECT COUNT(*) as plans_count FROM plans;"

# Количество супер-администраторов
docker exec autoservice_postgres psql -U autoservice_user -d autoservice_db -c "SELECT COUNT(*) as admins_count FROM super_admins;"
```

## 🎯 После успешного применения миграций

1. ✅ Перезапустите web контейнер
   ```bash
   docker-compose restart web
   ```

2. ✅ Проверьте работу API
   ```bash
   curl http://your_server.com:8000/api/health
   curl http://your_server.com:8000/api/public/plans
   ```

3. ✅ Откройте Frontend в браузере
   - Админ-панель: `http://your_server.com:3000`
   - Страница регистрации: `http://your_server.com:3000/register`

4. ✅ Войдите как супер-администратор
   - Username: `admin`
   - Email: `admin@autoservice.com`
   - Password: `admin123`

5. ✅ Измените пароль после первого входа!

## 📚 Дополнительная документация

- [Полное руководство по миграциям](../MIGRATION_GUIDE.md)
- [Настройка переменных окружения](../ENV_SETUP_GUIDE.md)
- [Сводка по миграциям](../MIGRATION_SUMMARY.md)
- [SQL скрипты](../sql/README.md)

## 🔗 Полезные команды

```bash
# Логи web контейнера
docker logs -f autoservice_web

# Логи PostgreSQL
docker logs -f autoservice_postgres

# Статус контейнеров
docker ps

# Перезапуск всех сервисов
docker-compose restart

# Остановка всех сервисов
docker-compose down

# Запуск всех сервисов
docker-compose up -d
```

---

**Для автоматического применения миграций используйте скрипт:**
```bash
./deploy/apply_migrations_remote.sh
```

**Для ручного применения используйте один из способов выше.**

