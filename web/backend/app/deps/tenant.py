"""
Dependency helpers для мульти-тенантности.

Единый стандарт:
- определение company_id (query → request.state → JWT)
- получение tenant AsyncSession
"""

import logging
from typing import AsyncGenerator, Optional

from fastapi import HTTPException, Query, Request
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.tenant_service import get_tenant_service

logger = logging.getLogger(__name__)


def _parse_company_id(value: object) -> Optional[int]:
    """Безопасно привести company_id к int."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def resolve_company_id(request: Request, company_id_query: Optional[int]) -> Optional[int]:
    """
    Определить company_id для tenant запроса.

    Порядок:
    1) query param company_id
    2) request.state.company_id
    3) JWT claim company_id
    """
    # 1) query param
    company_id = _parse_company_id(company_id_query)
    if company_id:
        request.state.company_id = company_id
        return company_id

    # 2) request.state
    state_company_id = getattr(request.state, "company_id", None)
    company_id = _parse_company_id(state_company_id)
    if company_id:
        return company_id

    # 3) JWT
    authorization = request.headers.get("Authorization") or ""
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        company_id = _parse_company_id(payload.get("company_id"))
        if company_id:
            request.state.company_id = company_id
            return company_id
        return None
    except Exception as e:
        logger.warning(f"Не удалось получить company_id из JWT: {e}")
        return None


async def get_tenant_db(
    request: Request,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: получить tenant AsyncSession по company_id.
    """
    resolved_company_id = await resolve_company_id(request, company_id)
    if not resolved_company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")

    tenant_service = get_tenant_service()
    async for session in tenant_service.get_tenant_session(resolved_company_id):
        yield session

