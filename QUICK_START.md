# 🚀 Быстрый запуск проекта Barber SaaS

## 📋 Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Минимум: 4GB RAM, 20GB диск

## ⚡ Быстрый старт

### 1. Настройка переменных окружения

```bash
# Скопируйте пример файла
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

**Минимально необходимые переменные для запуска:**

```env
DB_PASSWORD=your_strong_password_here
WEB_SECRET_KEY=your_32_character_secret_key_here
SUPER_ADMIN_EMAIL=admin@barber-saas.com
SUPER_ADMIN_PASSWORD=admin123
SUPER_ADMIN_TELEGRAM_ID=your_telegram_id
```

**Для генерации SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Запуск проекта

```bash
# Сборка и запуск всех сервисов
docker compose up -d --build

# Проверка статуса
docker compose ps
```

### 3. Применение миграций базы данных

```bash
# Применить все миграции
docker compose exec web python -m alembic upgrade head

# Проверить текущую версию
docker compose exec web alembic current
```

### 4. Создание начальных данных и супер-админа

```bash
# Создать тарифные планы и супер-администратора
docker compose exec web python scripts/seed.py
```

**После выполнения вы увидите:**
```
👑 Создание супер-администратора...
  ✅ Супер-администратор admin создан
  📧 Email: admin@barber-saas.com
  🔐 Пароль: admin123
  ⚠️  Не забудьте изменить пароль после первого входа!
```

### 5. Проверка работы

**Frontend:** http://localhost:3000  
**Backend API:** http://localhost:8000  
**API Docs (Swagger):** http://localhost:8000/docs  
**API Docs (ReDoc):** http://localhost:8000/redoc

**Супер-админ панель:** http://localhost:3000/super-admin/login

**Данные для входа:**
- Email: `admin@barber-saas.com` (или значение из SUPER_ADMIN_EMAIL)
- Пароль: `admin123` (или значение из SUPER_ADMIN_PASSWORD)

## 🔍 Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs web -f
docker compose logs bot -f
docker compose logs postgres -f
```

## 🛠️ Полезные команды

### Остановка проекта
```bash
docker compose down
```

### Перезапуск сервиса
```bash
docker compose restart web
docker compose restart bot
```

### Подключение к базе данных
```bash
docker compose exec postgres psql -U barber_user -d barber_db
```

### Выполнение команд в контейнере
```bash
docker compose exec web python scripts/seed.py
docker compose exec web python -m alembic upgrade head
```

## 🔐 Создание/изменение супер-админа

### Создание нового супер-админа

Если нужно создать супер-админа вручную:

```bash
docker compose exec web python
```

```python
import asyncio
from passlib.context import CryptContext
from sqlalchemy import text
from app.services.tenant_service import get_session_with_schema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_super_admin():
    async for session in get_session_with_schema("public"):
        admin_data = {
            'username': 'admin',
            'email': 'admin@barber-saas.com',
            'password_hash': pwd_context.hash('your_password_here'),
            'is_super_admin': True,
            'is_active': True
        }
        
        await session.execute(text("""
            INSERT INTO super_admins (username, email, password_hash, is_super_admin, is_active)
            VALUES (:username, :email, :password_hash, :is_super_admin, :is_active)
        """), admin_data)
        
        await session.commit()
        print("✅ Супер-админ создан!")

asyncio.run(create_super_admin())
```

### Изменение пароля супер-админа

```bash
# Используйте готовый скрипт
docker compose exec web python scripts/fix_super_admin_password.py
```

Или вручную через Python:

```bash
docker compose exec web python
```

```python
import asyncio
from passlib.context import CryptContext
from sqlalchemy import text
from app.services.tenant_service import get_session_with_schema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def change_password():
    async for session in get_session_with_schema("public"):
        new_password = 'new_password_here'
        email = 'admin@barber-saas.com'
        
        await session.execute(text("""
            UPDATE super_admins 
            SET password_hash = :password_hash 
            WHERE email = :email
        """), {
            'password_hash': pwd_context.hash(new_password),
            'email': email
        })
        
        await session.commit()
        print(f"✅ Пароль для {email} изменен!")

asyncio.run(change_password())
```

## ⚠️ Решение проблем

### Проблема: Контейнеры не запускаются

```bash
# Проверьте логи
docker compose logs

# Пересоберите контейнеры
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Проблема: База данных не подключается

```bash
# Проверьте, что PostgreSQL запущен
docker compose ps postgres

# Проверьте переменные окружения
docker compose exec postgres printenv | grep DB

# Проверьте подключение
docker compose exec postgres psql -U barber_user -d barber_db -c "SELECT 1;"
```

### Проблема: Миграции не применяются

```bash
# Проверьте текущую версию
docker compose exec web alembic current

# Примените миграции принудительно
docker compose exec web alembic upgrade head

# Если нужно откатить
docker compose exec web alembic downgrade -1
```

### Проблема: Супер-админ не создается

```bash
# Проверьте, что таблица super_admins существует
docker compose exec postgres psql -U barber_user -d barber_db -c "\dt public.super_admins"

# Запустите seed скрипт снова
docker compose exec web python scripts/seed.py
```

## 📝 Следующие шаги

1. ✅ Проект запущен
2. ✅ Супер-админ создан
3. ⏳ Войдите в супер-админ панель: http://localhost:3000/super-admin/login
4. ⏳ Измените пароль супер-админа
5. ⏳ Создайте первую компанию (салон красоты) через регистрацию: http://localhost:3000/register

---

**Готово!** Проект запущен и готов к работе! 🎉
