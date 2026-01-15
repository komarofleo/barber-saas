"""
Unit тесты для tenant dependencies (get_tenant_db, resolve_company_id).

Проверяет:
- Правильное определение company_id из разных источников
- Работу get_tenant_db dependency
- Обработку ошибок при отсутствии company_id
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, Request

from app.deps.tenant import resolve_company_id, get_tenant_db


class TestResolveCompanyId:
    """Тесты для функции resolve_company_id."""
    
    @pytest.mark.asyncio
    async def test_resolve_from_query_param(self):
        """Тест определения company_id из query параметра."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {}
        
        company_id = await resolve_company_id(request, 123)
        
        assert company_id == 123
        assert request.state.company_id == 123
    
    @pytest.mark.asyncio
    async def test_resolve_from_request_state(self):
        """Тест определения company_id из request.state."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = 456
        request.headers = {}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id == 456
    
    @pytest.mark.asyncio
    async def test_resolve_from_jwt_token(self):
        """Тест определения company_id из JWT токена."""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        # Создаем валидный JWT токен
        payload = {
            "sub": 1,
            "company_id": 789,
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {"Authorization": f"Bearer {token}"}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id == 789
        assert request.state.company_id == 789
    
    @pytest.mark.asyncio
    async def test_resolve_priority_query_over_state(self):
        """Тест приоритета query параметра над request.state."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = 456
        request.headers = {}
        
        company_id = await resolve_company_id(request, 123)
        
        assert company_id == 123  # Query параметр имеет приоритет
        assert request.state.company_id == 123
    
    @pytest.mark.asyncio
    async def test_resolve_priority_state_over_jwt(self):
        """Тест приоритета request.state над JWT."""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": 1,
            "company_id": 789,
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = 456
        request.headers = {"Authorization": f"Bearer {token}"}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id == 456  # request.state имеет приоритет над JWT
    
    @pytest.mark.asyncio
    async def test_resolve_none_when_no_sources(self):
        """Тест возврата None когда нет источников company_id."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id is None
    
    @pytest.mark.asyncio
    async def test_resolve_invalid_jwt_token(self):
        """Тест обработки невалидного JWT токена."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {"Authorization": "Bearer invalid_token"}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id is None
    
    @pytest.mark.asyncio
    async def test_resolve_jwt_without_company_id(self):
        """Тест обработки JWT токена без company_id."""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": 1,
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {"Authorization": f"Bearer {token}"}
        
        company_id = await resolve_company_id(request, None)
        
        assert company_id is None


class TestGetTenantDb:
    """Тесты для dependency get_tenant_db."""
    
    @pytest.mark.asyncio
    async def test_get_tenant_db_success(self, initialized_tenant_schema):
        """Тест успешного получения tenant сессии."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = initialized_tenant_schema
        request.headers = {}
        
        # Получаем tenant сессию
        async for session in get_tenant_db(request, initialized_tenant_schema):
            assert session is not None
            # Проверяем, что search_path установлен правильно
            from sqlalchemy import text
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            assert f"tenant_{initialized_tenant_schema}" in search_path
            break
    
    @pytest.mark.asyncio
    async def test_get_tenant_db_no_company_id(self):
        """Тест ошибки при отсутствии company_id."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            async for _ in get_tenant_db(request, None):
                pass
        
        assert exc_info.value.status_code == 400
        assert "company_id не найден" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_tenant_db_invalid_company_id(self):
        """Тест ошибки при невалидном company_id."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.company_id = None
        request.headers = {}
        
        # Используем несуществующий company_id
        with pytest.raises(HTTPException) as exc_info:
            async for _ in get_tenant_db(request, 999999):
                pass
        
        # Может быть ошибка 400 (company_id не найден) или другая ошибка от tenant_service
        assert exc_info.value.status_code in [400, 500]
