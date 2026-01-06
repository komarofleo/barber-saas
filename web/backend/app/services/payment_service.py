"""
Сервис для работы с платежами в public схеме.

Обеспечивает:
- CRUD операции для Payment модели
- Интеграцию с Юкассой
- Обработку webhook уведомлений
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.public_models import Payment, Subscription, Company
from app.services.yookassa_service import YooKassaService
from app.config import settings

logger = logging.getLogger(__name__)


async def get_payment_by_id(
    session: AsyncSession,
    payment_id: int
) -> Optional[Payment]:
    """
    Получить платеж по ID.
    
    Args:
        session: Асинхронная сессия БД
        payment_id: ID платежа
        
    Returns:
        Объект Payment или None
    """
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def get_payments_by_company(
    session: AsyncSession,
    company_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Payment]:
    """
    Получить список платежей компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        status: Фильтр по статусу (опционально)
        skip: Сколько записей пропустить
        limit: Сколько записей получить
        
    Returns:
        Список платежей
    """
    query = select(Payment).where(Payment.company_id == company_id)
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.order_by(Payment.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_payments_by_subscription(
    session: AsyncSession,
    subscription_id: int,
    status: Optional[str] = None,
) -> List[Payment]:
    """
    Получить список платежей подписки.
    
    Args:
        session: Асинхронная сессия БД
        subscription_id: ID подписки
        status: Фильтр по статусу (опционально)
        
    Returns:
        Список платежей
    """
    query = select(Payment).where(Payment.subscription_id == subscription_id)
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.order_by(Payment.created_at.desc())
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_payment(
    session: AsyncSession,
    company_id: int,
    subscription_id: int,
    amount: Decimal,
    payment_method: str = "yookassa",
    metadata: Optional[Dict[str, Any]] = None,
) -> Payment:
    """
    Создать запись о платеже.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        subscription_id: ID подписки
        amount: Сумма платежа
        payment_method: Способ оплаты (по умолчанию "yookassa")
        metadata: Дополнительные метаданные
        
    Returns:
        Созданный объект Payment
    """
    payment = Payment(
        company_id=company_id,
        subscription_id=subscription_id,
        amount=amount,
        currency="RUB",
        payment_method=payment_method,
        status="pending",  # В начале платеж в ожидании
        metadata=metadata or {},
    )
    
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    
    logger.info(f"Создан платеж: {amount} RUB для компании {company_id}")
    
    return payment


async def update_payment_status(
    session: AsyncSession,
    payment_id: int,
    status: str,
    metadata: Optional[Dict[str, Any]] = None,
    yookassa_payment_id: Optional[str] = None,
) -> bool:
    """
    Обновить статус платежа.
    
    Args:
        session: Асинхронная сессия БД
        payment_id: ID платежа
        status: Новый статус (pending, succeeded, failed, cancelled)
        metadata: Дополнительные метаданные
        yookassa_payment_id: ID платежа в Юкассе
        
    Returns:
        True, если платеж успешно обновлен, иначе False
    """
    payment = await get_payment_by_id(session, payment_id)
    
    if not payment:
        logger.error(f"Платеж с ID {payment_id} не найден")
        return False
    
    payment.status = status
    
    if metadata:
        if payment.metadata is None:
            payment.metadata = {}
        payment.metadata.update(metadata)
    
    if yookassa_payment_id:
        if payment.metadata is None:
            payment.metadata = {}
        payment.metadata["yookassa_payment_id"] = yookassa_payment_id
    
    await session.commit()
    
    logger.info(f"Обновлен платеж {payment_id}: статус={status}")
    
    return True


async def process_webhook(
    session: AsyncSession,
    event: Dict[str, Any],
) -> Optional[Payment]:
    """
    Обработать webhook от Юкассы.
    
    Args:
        session: Асинхронная сессия БД
        event: Данные webhook от Юкассы
        
    Returns:
        Обновленный платеж или None
    """
    event_type = event.get("event")
    
    if event_type == "payment.succeeded":
        # Платеж успешен - активируем подписку
        object_data = event.get("object", {})
        payment_data = object_data.get("payment", {})
        metadata_data = payment_data.get("metadata", {})
        
        yookassa_payment_id = payment_data.get("id")
        subscription_id = metadata_data.get("subscription_id")
        company_id = metadata_data.get("company_id")
        
        if not subscription_id or not company_id:
            logger.error(f"В webhook нет subscription_id или company_id")
            return None
        
        # Обновляем статус платежа
        payment = await update_payment_status(
            session=session,
            payment_id=subscription_id,  # В metadata может быть payment_id
            status="succeeded",
            metadata=metadata_data,
            yookassa_payment_id=yookassa_payment_id,
        )
        
        if payment:
            # Активируем подписку
            from app.services.subscription_service import activate_subscription
            
            subscription_end_date = await activate_subscription(
                session=session,
                subscription_id=subscription_id,
                end_date=date.today() + datetime.timedelta(days=30),  # +30 дней
            )
            
            if subscription_end_date:
                logger.info(f"Подписка {subscription_id} активирована до {subscription_end_date}")
    
    elif event_type == "payment.canceled":
        # Платеж отменен
        object_data = event.get("object", {})
        payment_data = object_data.get("payment", {})
        metadata_data = payment_data.get("metadata", {})
        
        yookassa_payment_id = payment_data.get("id")
        subscription_id = metadata_data.get("subscription_id")
        
        if not subscription_id:
            logger.error(f"В webhook нет subscription_id")
            return None
        
        # Обновляем статус платежа
        payment = await update_payment_status(
            session=session,
            payment_id=subscription_id,
            status="cancelled",
            metadata=metadata_data,
            yookassa_payment_id=yookassa_payment_id,
        )
        
        if payment:
            logger.info(f"Платеж {yookassa_payment_id} отменен")
    
    elif event_type == "payment.failed":
        # Платеж не удался
        object_data = event.get("object", {})
        payment_data = object_data.get("payment", {})
        metadata_data = payment_data.get("metadata", {})
        
        yookassa_payment_id = payment_data.get("id")
        subscription_id = metadata_data.get("subscription_id")
        
        if not subscription_id:
            logger.error(f"В webhook нет subscription_id")
            return None
        
        # Обновляем статус платежа
        payment = await update_payment_status(
            session=session,
            payment_id=subscription_id,
            status="failed",
            metadata=metadata_data,
            yookassa_payment_id=yookassa_payment_id,
        )
        
        if payment:
            logger.info(f"Платеж {yookassa_payment_id} не удался")
    
    return payment


async def create_yookassa_payment(
    session: AsyncSession,
    company_id: int,
    subscription_id: int,
    amount: Decimal,
    description: str,
    return_url: str,
) -> Dict[str, Any]:
    """
    Создать платеж через Юкассу.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        subscription_id: ID подписки
        amount: Сумма платежа
        description: Описание платежа
        return_url: URL для возврата после оплаты
        
    Returns:
        Словарь с данными платежа из Юкассы
    """
    yookassa_service = YooKassaService()
    
    # Создаем метаданные для Юкассы
    metadata = {
        "company_id": company_id,
        "subscription_id": subscription_id,
    }
    
    # Создаем платеж через Юкассу
    payment_response = await yookassa_service.create_payment(
        amount=float(amount),
        description=description,
        metadata=metadata,
        return_url=return_url,
    )
    
    if not payment_response or "id" not in payment_response:
        logger.error("Не удалось создать платеж через Юкассу")
        return {
            "success": False,
            "error": "Не удалось создать платеж"
        }
    
    # Создаем запись о платеже в БД
    payment = await create_payment(
        session=session,
        company_id=company_id,
        subscription_id=subscription_id,
        amount=amount,
        metadata=metadata,
    )
    
    return {
        "success": True,
        "payment_id": payment.id,
        "yookassa_payment_id": payment_response.get("id"),
        "confirmation_url": payment_response.get("confirmation_url"),
    }


async def verify_webhook_signature(
    payload: str,
    signature: str,
) -> bool:
    """
    Проверить подпись webhook от Юкассы.
    
    Args:
        payload: Тело запроса
        signature: Подпись из заголовка
        
    Returns:
        True, если подпись валидна, иначе False
    """
    yookassa_service = YooKassaService()
    return await yookassa_service.verify_webhook_signature(payload, signature)

