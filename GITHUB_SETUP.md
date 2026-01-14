# 🚀 Настройка GitHub для проекта Barber SaaS

## ✅ Репозиторий создан

Репозиторий успешно создан на GitHub:
- **URL:** https://github.com/komarofleo/barber-saas
- **SSH:** git@github.com:komarofleo/barber-saas.git
- **HTTPS:** https://github.com/komarofleo/barber-saas.git

## 📋 Инструкции по настройке

### 1. Инициализация Git (если еще не инициализирован)

```bash
cd /Users/komarofleo/ai/barber
git init
```

### 2. Добавление remote репозитория

```bash
git remote add origin https://github.com/komarofleo/barber-saas.git
# или через SSH (если настроен ключ):
# git remote add origin git@github.com:komarofleo/barber-saas.git
```

### 3. Проверка текущего состояния

```bash
git status
```

### 4. Создание .gitignore (если еще нет)

Убедитесь, что у вас есть `.gitignore` файл со следующим содержимым:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite

# Logs
*.log

# Docker
docker-compose.override.yml

# Node
node_modules/
npm-debug.log*

# Build
dist/
build/
*.egg-info/

# Backup files
*.sql
backups/
*.tar.gz
*.zip

# OS
.DS_Store
Thumbs.db
```

### 5. Первый коммит и push

```bash
# Добавить все файлы
git add .

# Создать первый коммит
git commit -m "feat: Переименование проекта с AutoService на Barber SaaS

- Обновлена вся терминология: автосервис → салон красоты
- Заменены все упоминания AutoService на Barber
- Обновлены домены: barber-saas.com
- Обновлены email адреса: support@barber-saas.com
- Заменено 'пост' на 'рабочее место' в пользовательских сообщениях
- Обновлены Docker контейнеры: barber_*
- Обновлены все md файлы документации
- Обновлен код backend, frontend и bot"

# Переименовать ветку в main (если нужно)
git branch -M main

# Push в GitHub
git push -u origin main
```

### 6. Настройка для локальной разработки

Так как проект запускается на localhost, убедитесь, что в `.env` файле указаны правильные настройки:

```env
# База данных
DB_HOST=postgres
DB_PORT=5432
DB_NAME=barber_db
DB_USER=barber_user
DB_PASSWORD=your_strong_password_here

# Web
WEB_SECRET_KEY=your_32_character_secret_key_here
WEB_HOST=0.0.0.0
WEB_PORT=8000

# Юкасса (для платежей)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_API_URL=https://api.yookassa.ru/v3
YOOKASSA_RETURN_URL=http://localhost:3000/success
YOOKASSA_WEBHOOK_URL=http://localhost:8000/api/public/webhooks/yookassa

# Redis (для Celery)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Супер-админ
SUPER_ADMIN_EMAIL=admin@barber-saas.com
SUPER_ADMIN_PASSWORD=your_strong_password
SUPER_ADMIN_TELEGRAM_ID=your_telegram_id

# Супер-админ бот
SUPER_ADMIN_BOT_TOKEN=your_bot_token_from_botfather
```

### 7. Запуск проекта локально

```bash
# Запуск всех сервисов
docker compose up -d

# Применение миграций
docker compose exec web python -m alembic upgrade head

# Создание начальных данных
docker compose exec web python scripts/seed.py
```

## 🔗 Полезные ссылки

- **Репозиторий:** https://github.com/komarofleo/barber-saas
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 📝 Следующие шаги

1. ✅ Репозиторий создан
2. ⏳ Настроить Git remote и сделать первый push
3. ⏳ Настроить CI/CD (опционально)
4. ⏳ Настроить GitHub Actions для автоматических тестов (опционально)
5. ⏳ Добавить описание проекта в README.md на GitHub

---

**Дата создания:** 14.01.2026  
**Проект:** Barber SaaS v2.0
