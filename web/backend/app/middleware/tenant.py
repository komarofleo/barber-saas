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
from jose import jwt

from app.config import settings

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
        # Пытаемся извлечь company_id из JWT и положить в request.state.company_id.
        # Это НЕ переключает схему само по себе; схемой управляет dependency tenant-сессии.
        authorization = request.headers.get("Authorization") or ""
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "").strip()
            if token:
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                    company_id = payload.get("company_id")
                    if company_id is not None:
                        try:
                            request.state.company_id = int(company_id)
                        except (TypeError, ValueError):
                            # Не падаем на мусорном company_id
                            pass
                except Exception:
                    # Ошибки декодирования не считаем критичными для всех маршрутов
                    pass

        logger.info(f"Tenant middleware: {request.method} {request.url.path}")
        
        response = await call_next(request)
        return response
