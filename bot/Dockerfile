FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY bot/ ./bot/
COPY shared/ ./shared/
COPY scripts/ ./scripts/
COPY web/backend/ ./web/backend/

# Добавляем web/backend в PYTHONPATH для импорта app
ENV PYTHONPATH=/app/web/backend:/app

# Запуск бота
CMD ["python", "-m", "bot.main"]

