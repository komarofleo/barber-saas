#!/bin/bash
# Скрипт для запуска бэкенда локально

cd "$(dirname "$0")"
cd ../..

# Устанавливаем PYTHONPATH
export PYTHONPATH="$PWD:$PWD/web/backend:$PWD/shared"

# Запускаем uvicorn
cd web/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload



