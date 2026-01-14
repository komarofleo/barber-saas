# 🚀 Инструкция по запуску проекта Barber SaaS

## ⚡ Самый быстрый способ

```bash
# 1. Создайте .env файл (если еще нет)
cp .env.example .env

# 2. Отредактируйте .env и заполните минимум:
#    - DB_PASSWORD (любой надежный пароль)
#    - WEB_SECRET_KEY (можно сгенерировать: python3 -c "import secrets; print(secrets.token_urlsafe(32))")
#    - SUPER_ADMIN_PASSWORD (пароль для супер-админа)

# 3. Запустите скрипт
./start.sh
```

**Готово!** Проект запущен, супер-админ создан автоматически.

## 📋 Пошаговая инструкция

### Шаг 1: Настройка переменных окружения

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте файл
nano .env  # или используйте любой редактор
```

**Минимально необходимые переменные:**

```env
# Обязательно заполните эти:
DB_PASSWORD=your_strong_password_here
WEB_SECRET_KEY=your_32_character_secret_key_here
SUPER_ADMIN_PASSWORD=admin123

# Остальные можно оставить по умолчанию для localhost
```

**Генерация WEB_SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Шаг 2: Запуск Docker контейнеров

```bash
# Сборка и запуск
docker compose up -d --build

# Проверка статуса
docker compose ps
```

Должны запуститься:
- ✅ `barber_postgres` - база данных
- ✅ `barber_redis` - Redis для Celery
- ✅ `barber_web` - Backend API
- ✅ `barber_frontend` - Frontend
- ✅ `barber_bot` - Telegram бот
- ✅ `barber_celery_worker` - Celery worker
- ✅ `barber_celery_beat` - Celery beat

### Шаг 3: Применение миграций

```bash
# Применить все миграции базы данных
docker compose exec web python -m alembic upgrade head
```

### Шаг 4: Создание супер-админа

```bash
# Создать тарифные планы и супер-администратора
docker compose exec web python scripts/seed.py
```

**Вы увидите:**
```
👑 Создание супер-администратора...
  ✅ Супер-администратор admin создан
  📧 Email: admin@barber-saas.com
  🔐 Пароль: admin123
  ⚠️  Не забудьте изменить пароль после первого входа!
```

### Шаг 5: Проверка работы

Откройте в браузере:

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Супер-админ панель:** http://localhost:3000/super-admin/login

**Вход в супер-админ панель:**
- Email: `admin@barber-saas.com` (или из `SUPER_ADMIN_EMAIL`)
- Password: `admin123` (или из `SUPER_ADMIN_PASSWORD`)

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

### Проверка супер-админа в БД
```bash
docker compose exec postgres psql -U barber_user -d barber_db -c "SELECT username, email, is_active FROM super_admins;"
```

## ⚠️ Решение проблем

### Контейнеры не запускаются

```bash
# Проверьте логи
docker compose logs

# Пересоберите
docker compose down
docker compose build --no-cache
docker compose up -d
```

### База данных не подключается

```bash
# Проверьте переменные
docker compose exec postgres printenv | grep DB

# Проверьте подключение
docker compose exec postgres psql -U barber_user -d barber_db -c "SELECT 1;"
```

### Супер-админ не создается

```bash
# Проверьте таблицу
docker compose exec postgres psql -U barber_user -d barber_db -c "\dt public.super_admins"

# Запустите seed снова
docker compose exec web python scripts/seed.py
```

### Миграции не применяются

```bash
# Проверьте текущую версию
docker compose exec web alembic current

# Примените принудительно
docker compose exec web alembic upgrade head
```

## 📝 Следующие шаги после запуска

1. ✅ Войдите в супер-админ панель
2. ✅ Измените пароль супер-админа
3. ✅ Создайте первую компанию через регистрацию: http://localhost:3000/register
4. ✅ Настройте Telegram бота для компании

---

**Готово!** Проект запущен и готов к работе! 🎉

Для подробной информации см.:
- [QUICK_START.md](QUICK_START.md) - быстрый старт
- [CREATE_SUPER_ADMIN.md](CREATE_SUPER_ADMIN.md) - создание супер-админа
- [README.md](README.md) - полная документация
