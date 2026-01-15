"""
Общие fixtures для всех тестов.

Содержит:
- Настройка тестовой БД
- Fixtures для tenant сервиса
- Fixtures для сессий БД
- Fixtures для создания тестовых данных
"""
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Настраиваем переменные окружения для тестов перед импортом settings
os.environ.setdefault('TESTING', 'true')

from app.config import settings
from app.services.tenant_service import get_tenant_service
from app.database import async_session_maker


# Тестовая БД (можно использовать in-memory SQLite или отдельную тестовую PostgreSQL)
TEST_DATABASE_URL = getattr(settings, "TEST_DATABASE_URL", None) or (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Создать engine для тестовой БД."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool if "sqlite" in TEST_DATABASE_URL else None,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_maker(test_engine):
    """Создать session maker для тестовой БД."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture для получения тестовой сессии БД.
    
    Использует транзакцию, которая откатывается после теста.
    """
    async with test_session_maker() as session:
        # Начинаем транзакцию
        trans = await session.begin()
        try:
            yield session
        finally:
            # Откатываем транзакцию
            await trans.rollback()
            await session.close()


@pytest_asyncio.fixture
async def tenant_service():
    """
    Fixture для получения TenantService.
    
    Использует реальный сервис, но можно переопределить для тестов.
    """
    return get_tenant_service()


@pytest_asyncio.fixture
async def test_company_id() -> int:
    """
    Fixture для получения тестового company_id.
    
    Можно использовать для создания тестовых tenant схем.
    """
    return 99999  # Используем большой ID, чтобы не конфликтовать с реальными данными


@pytest_asyncio.fixture
async def clean_tenant_schema(tenant_service, test_company_id):
    """
    Fixture для очистки tenant схемы перед и после теста.
    
    Удаляет схему перед тестом и после теста.
    """
    # Удаляем схему перед тестом (если существует)
    await tenant_service.drop_tenant_schema(test_company_id)
    
    yield test_company_id
    
    # Удаляем схему после теста
    await tenant_service.drop_tenant_schema(test_company_id)


@pytest_asyncio.fixture
async def initialized_tenant_schema(tenant_service, clean_tenant_schema):
    """
    Fixture для инициализированной tenant схемы.
    
    Создает и инициализирует tenant схему для теста.
    """
    company_id = clean_tenant_schema
    await tenant_service.create_tenant_schema(company_id)
    await tenant_service.initialize_tenant_for_company(company_id)
    return company_id


@pytest_asyncio.fixture
async def tenant_session(tenant_service, initialized_tenant_schema):
    """
    Fixture для получения tenant сессии.
    
    Возвращает сессию с установленным search_path для tenant схемы.
    """
    company_id = initialized_tenant_schema
    async for session in tenant_service.get_tenant_session(company_id):
        yield session
        break


@pytest.fixture
def mock_request():
    """Fixture для создания mock Request объекта."""
    from unittest.mock import Mock
    from fastapi import Request
    
    request = Mock(spec=Request)
    request.state = Mock()
    request.state.company_id = None
    request.headers = {}
    return request


@pytest.fixture
def mock_user():
    """Fixture для создания mock User объекта."""
    from unittest.mock import Mock
    from shared.database.models import User
    
    user = Mock(spec=User)
    user.id = 1
    user.full_name = "Test User"
    user.phone = "+79991234567"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_admin = True
    user.telegram_id = 123456789
    return user


@pytest.fixture
def sample_jwt_token():
    """Fixture для создания тестового JWT токена."""
    from jose import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": 1,  # user_id
        "company_id": 99999,
        "exp": datetime.utcnow() + timedelta(days=1),
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
