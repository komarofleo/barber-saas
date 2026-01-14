# 👑 Создание супер-администратора

## 🚀 Быстрый способ (рекомендуется)

### Автоматическое создание через seed скрипт

```bash
# Запустите скрипт создания начальных данных
docker compose exec web python scripts/seed.py
```

Этот скрипт:
- ✅ Создает тарифные планы (Starter, Pro, Business)
- ✅ Создает супер-администратора

**Данные супер-админа по умолчанию:**
- Username: `admin` (из переменной `SUPER_ADMIN_USERNAME`)
- Email: `admin@barber-saas.com` (из переменной `SUPER_ADMIN_EMAIL`)
- Password: `admin123` (из переменной `SUPER_ADMIN_PASSWORD`)

## 📝 Настройка через .env файл

Перед запуском seed скрипта настройте переменные в `.env`:

```env
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_EMAIL=admin@barber-saas.com
SUPER_ADMIN_PASSWORD=your_secure_password_here
SUPER_ADMIN_TELEGRAM_ID=your_telegram_id
```

## 🔧 Ручное создание через Python

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
        print(f"   Email: {admin_data['email']}")
        print(f"   Username: {admin_data['username']}")

asyncio.run(create_super_admin())
```

## 🔐 Изменение пароля супер-админа

### Способ 1: Через готовый скрипт

```bash
docker compose exec web python scripts/fix_super_admin_password.py
```

Этот скрипт проверяет и обновляет пароль на `admin123`.

### Способ 2: Вручную через Python

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
        new_password = 'new_secure_password_here'
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
        print(f"✅ Пароль для {email} изменен на: {new_password}")

asyncio.run(change_password())
```

### Способ 3: Через SQL напрямую

```bash
docker compose exec postgres psql -U barber_user -d barber_db
```

```sql
-- Генерируем хеш пароля (нужно использовать Python для генерации правильного bcrypt хеша)
-- Лучше использовать Python скрипт выше
```

## ✅ Проверка создания супер-админа

```bash
# Проверить через SQL
docker compose exec postgres psql -U barber_user -d barber_db -c "SELECT username, email, is_active FROM super_admins;"
```

## 🔍 Вход в супер-админ панель

1. Откройте браузер: http://localhost:3000/super-admin/login
2. Введите:
   - **Email:** `admin@barber-saas.com` (или ваш из SUPER_ADMIN_EMAIL)
   - **Password:** `admin123` (или ваш из SUPER_ADMIN_PASSWORD)
3. Нажмите "Войти"

## ⚠️ Важные замечания

1. **Измените пароль после первого входа!**
2. **Не используйте простые пароли в production!**
3. **Храните .env файл в безопасности и не коммитьте его в Git!**

---

**Готово!** Супер-админ создан и готов к работе! 🎉
