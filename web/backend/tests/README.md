# 🧪 Тесты проекта Barber SaaS

## Структура тестов

```
tests/
├── __init__.py
├── conftest.py              # Общие fixtures
├── unit/                    # Unit тесты (быстрые, изолированные)
│   ├── __init__.py
│   ├── test_tenant_service.py
│   ├── test_tenant_deps.py
│   └── test_crud_clients.py
├── integration/            # Интеграционные тесты (требуют БД)
│   ├── __init__.py
│   ├── test_multi_tenant.py
│   └── test_tenant_isolation.py
└── e2e/                    # End-to-end тесты (полный поток)
    ├── __init__.py
    └── test_booking_flow.py
```

## Установка зависимостей

```bash
pip install -r requirements.txt
```

Или только тестовые зависимости:
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

## Запуск тестов

### Все тесты
```bash
cd web/backend
pytest
```

### Только unit тесты
```bash
pytest tests/unit/ -v
```

### Только интеграционные тесты
```bash
pytest tests/integration/ -v -m integration
```

### Только E2E тесты
```bash
pytest tests/e2e/ -v -m e2e
```

### С покрытием кода
```bash
pytest --cov=app --cov-report=html
```

### Конкретный тест
```bash
pytest tests/unit/test_crud_clients.py::test_create_client -v
```

## Маркеры тестов

- `@pytest.mark.unit` - Unit тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.e2e` - E2E тесты
- `@pytest.mark.tenant` - Тесты мульти-тенантности
- `@pytest.mark.api` - Тесты API endpoints
- `@pytest.mark.crud` - Тесты CRUD операций
- `@pytest.mark.slow` - Медленные тесты

## Примеры использования маркеров

```bash
# Только быстрые unit тесты
pytest -m "unit and not slow"

# Только тесты мульти-тенантности
pytest -m tenant

# Все кроме E2E
pytest -m "not e2e"
```

## Настройка тестовой БД

По умолчанию тесты используют БД из `settings.TEST_DATABASE_URL` или создают отдельную тестовую БД.

Для настройки тестовой БД создайте `.env.test`:
```env
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/barber_test
```

## Fixtures

### `db_session`
Тестовая сессия БД с автоматическим откатом транзакций.

### `tenant_service`
Экземпляр TenantService для работы с tenant схемами.

### `test_company_id`
Тестовый company_id (99999) для создания tenant схем.

### `clean_tenant_schema`
Автоматически очищает tenant схему перед и после теста.

### `initialized_tenant_schema`
Создает и инициализирует tenant схему для теста.

### `tenant_session`
Возвращает сессию с установленным search_path для tenant схемы.

### `mock_request`
Mock объект Request для тестирования API endpoints.

### `mock_user`
Mock объект User для тестирования с авторизацией.

## Написание новых тестов

### Unit тест
```python
import pytest
import pytest_asyncio

@pytest_asyncio.mark.asyncio
async def test_my_function(mock_user, mock_request):
    """Тест моей функции."""
    # Arrange
    # Act
    # Assert
    assert True
```

### Интеграционный тест
```python
import pytest
import pytest_asyncio

@pytest_asyncio.mark.integration
@pytest_asyncio.mark.asyncio
async def test_my_integration(tenant_session, initialized_tenant_schema):
    """Интеграционный тест."""
    company_id = initialized_tenant_schema
    # Тестируем с реальной БД
    assert True
```

### E2E тест
```python
import pytest
import pytest_asyncio

@pytest_asyncio.mark.e2e
@pytest_asyncio.mark.asyncio
async def test_full_flow(tenant_session, mock_user, mock_request):
    """E2E тест полного потока."""
    # Тестируем полный поток работы
    assert True
```

## Покрытие кода

Минимальное покрытие установлено в 60% (`--cov-fail-under=60`).

Для просмотра отчета:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Ошибка "database does not exist"
Создайте тестовую БД:
```bash
createdb barber_test
```

### Ошибка "schema does not exist"
Тесты автоматически создают и удаляют tenant схемы. Убедитесь, что у пользователя БД есть права на создание схем.

### Медленные тесты
Используйте маркер `@pytest.mark.slow` и запускайте их отдельно:
```bash
pytest -m "not slow"  # Только быстрые тесты
```

## CI/CD

Тесты должны запускаться в CI/CD пайплайне перед деплоем:
```yaml
- name: Run tests
  run: |
    cd web/backend
    pytest --cov=app --cov-report=xml
```
