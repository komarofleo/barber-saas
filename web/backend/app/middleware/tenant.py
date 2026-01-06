"""
Middleware для мульти-тенантности.

Обеспечивает:
- Извлечение company_id из JWT токена
- Сохранение company_id в request.state
- Переключение на tenant схему
"""
import logging
from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware для мульти-тенантности.
    
    Извлекает company_id из JWT токена и сохраняет в request.state.
    CRUD operations используют get_tenant_session(company_id) для работы с tenant схемой.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Обработка запроса с мульти-тенантностью.
        
        Args:
            request: FastAPI Request объект
            call_next: Следующая middleware или route handler
            
        Returns:
            Response от route handler
        """
        # TODO: В будущем здесь будет извлечение company_id из JWT токена
        # request.state.company_id = company_id
        
        # На данный момент просто пропускаем запрос
        # CRUD operations будут сами вызывать get_tenant_session()
        
        logger.info(f"Tenant middleware: {request.method} {request.url.path}")
        
        response = await call_next(request)
        return response
