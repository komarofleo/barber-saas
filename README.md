# 🚗 AutoService - Система бронирования для автосервиса

Полнофункциональная система управления записями в автосервисе с Telegram-ботом и веб-админ панелью.

## 🚀 Быстрый старт

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- Минимум: 2GB RAM, 10GB диск

### Установка

1. **Создайте файл `.env`** на основе `.env.example`:
```bash
cp .env.example .env
nano .env
```

2. **Заполните обязательные переменные:**
```env
BOT_TOKEN=8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4
ADMIN_IDS=329621295
DB_PASSWORD=your_strong_password_here
WEB_SECRET_KEY=your_32_character_secret_key_here
```

3. **Запустите проект:**
```bash
docker compose build
docker compose up -d
```

4. **Инициализируйте базу данных:**
```bash
# Применение миграций (если есть)
docker compose exec web alembic upgrade head

# Создание начальных данных
docker compose exec bot python scripts/init_data.py

# Создание администратора (если нужно)
docker compose exec web python scripts/create_admin.py --telegram-id 329621295
```

5. **Проверка работы:**
```bash
# Логи бота
docker compose logs bot -f

# Логи backend
docker compose logs web -f
```

## 📁 Структура проекта

```
autoservice/
├── bot/                    # Telegram бот
│   ├── handlers/          # Обработчики
│   ├── keyboards/         # Клавиатуры
│   ├── database/          # CRUD операции
│   └── main.py           # Точка входа
├── web/                   # Веб-панель
│   ├── backend/          # FastAPI
│   └── frontend/         # React
├── shared/               # Общий код
│   └── database/         # Модели БД
└── scripts/              # Скрипты
```

## 🔧 Команды

- `docker compose up -d` - Запуск всех сервисов
- `docker compose down` - Остановка всех сервисов
- `docker compose logs -f` - Просмотр логов
- `docker compose ps` - Статус контейнеров

## 📞 Поддержка

При возникновении проблем проверьте логи:
```bash
docker compose logs bot | tail -50
docker compose logs web | tail -50
```









