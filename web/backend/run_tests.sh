#!/bin/bash
# Скрипт для запуска тестов

set -e

echo "🧪 Запуск тестов проекта Barber SaaS"
echo ""

# Переходим в директорию backend
cd "$(dirname "$0")"

# Проверяем, установлен ли pytest
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest не установлен. Установите зависимости:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Парсим аргументы
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    unit)
        echo "📦 Запуск unit тестов..."
        pytest tests/unit/ -v $VERBOSE
        ;;
    integration)
        echo "🔗 Запуск интеграционных тестов..."
        pytest tests/integration/ -v -m integration $VERBOSE
        ;;
    e2e)
        echo "🌐 Запуск E2E тестов..."
        pytest tests/e2e/ -v -m e2e $VERBOSE
        ;;
    coverage)
        echo "📊 Запуск тестов с покрытием кода..."
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo "✅ Отчет сохранен в htmlcov/index.html"
        ;;
    all|*)
        echo "🚀 Запуск всех тестов..."
        pytest -v $VERBOSE
        ;;
esac

echo ""
echo "✅ Тесты завершены!"
