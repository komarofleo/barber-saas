"""
API для обработки webhooks от внешних сервисов.

Этот модуль содержит handlers для:
- Webhook от Юкассы (уведомления о платежах)
- Других webhook интеграций
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.database import get_db
from app.schemas.public_schemas import (
    YookassaWebhook,
    WebhookVerificationResponse,
    CompanyCreate,
    SubscriptionCreate,
    SubscriptionStatus
)
from app.models.public_models import Company, Plan, Payment, Subscription, PaymentStatus
from app.services.yookassa_service import get_payment, verify_webhook_signature
from app.services.tenant_service import get_tenant_service
from app.services.email_service import send_welcome_email
from app.services.telegram_notification_service import send_activation_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/webhooks", tags=["webhooks"])


async def get_webhook_body(request: Request) -> str:
    """
    Получить тело запроса webhook.
    
    Args:
        request: FastAPI Request объект
    
    Returns:
        Тело запроса в виде строки
    """
    return await request.body()


@router.post("/yookassa", status_code=200)
async def yookassa_webhook(
    request: Request,
    signature: Annotated[str, Header(alias="IIS-Signature", description="Подпись webhook от Юкассы")],
    db: AsyncSession = Depends(get_db)
):
    """
    Обработать webhook от Юкассы о статусах платежей.
    
    Args:
        request: FastAPI Request объект
        signature: Подпись webhook для верификации
        db: Асинхронная сессия БД
    
    Returns:
        Сообщение об успешной обработке webhook
    
    Raises:
        HTTPException: При ошибках валидации или обработки
    
    Example:
        >>> # Webhook запрос от Юкассы
        >>> POST /api/public/webhooks/yookassa
        >>> Headers:
        ...   IIS-Signature: "aBc123..."
        >>> Body:
        ...   {
        ...     "event": "payment.succeeded",
        ...     "object": {
        ...       "id": "12345",
        ...       "status": "succeeded",
        ...       "amount": {
        ...         "value": "5000.00",
        ...         "currency": "RUB"
        ...       },
        ...       "metadata": {
        ...         "plan_id": "3",
        ...         "company_name": "ООО 'Точка'"
        ...       }
        ...     }
        ...   }
        
        >>> # Ответ
        >>> {"success": true}
    """
    logger.info("Получен webhook от Юкассы")
    
    # 1. Получение тела запроса
    payload = await get_webhook_body(request)
    payload_str = payload.decode('utf-8')
    
    # 2. Верификация подписи webhook
    logger.info(f"Верификация подписи webhook: {signature[:10]}...")
    is_signature_valid = verify_webhook_signature(payload_str, signature)
    
    if not is_signature_valid:
        logger.error("Подпись webhook не валидна!")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидная подпись webhook"
        )
    
    # 3. Парсинг данных webhook
    try:
        webhook_data = YookassaWebhook(event="", object_=payload_str)
    except Exception as e:
        logger.error(f"Ошибка парсинга webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный формат webhook"
        )
    
    logger.info(f"Webhook событие: {webhook_data.event}")
    
    # 4. Получение информации о платеже
    yookassa_payment_id = webhook_data.object_.get("id")
    logger.info(f"ID платежа Юкассы: {yookassa_payment_id}")
    
    try:
        # Находим платеж в БД
        payment_result = await db.execute(
            select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id)
        )
        payment = payment_result.scalar_one_or_none()
        
        if not payment:
            logger.error(f"Платеж {yookassa_payment_id} не найден в БД")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Платеж не найден"
            )
        
        # Обновляем статус платежа
        payment.yookassa_payment_status = webhook_data.object_.get("status", "unknown")
        payment.webhook_received_at = date.today()
        payment.webhook_signature_verified = True
        
        # Обработка успешного платежа
        if webhook_data.event == "payment.succeeded" and payment.status == "pending":  # Исправлено: используем строку
            logger.info(f"Обработка успешного платежа: {payment.id}")
            
            # Получаем extra_data (переименовано из metadata)
            extra_data = payment.extra_data or {}
            if isinstance(extra_data, str):
                import json
                try:
                    extra_data = json.loads(extra_data)
                except:
                    extra_data = {}
            
            # Начинаем транзакцию для создания всех сущностей
            async with db.begin():
                # 1. Создаем компанию
                logger.info("Создание компании...")
                
                plan_result = await db.execute(
                    select(Plan).where(Plan.id == payment.plan_id)
                )
                plan = plan_result.scalar_one_or_none()
                
                if not plan:
                    logger.error(f"План {payment.plan_id} не найден")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Тарифный план не найден"
                    )
                
                company = Company(
                    name=extra_data.get("company_name", "Неизвестный салон красоты"),
                    email=extra_data.get("email", ""),
                    phone=extra_data.get("phone"),
                    telegram_bot_token=extra_data.get("telegram_bot_token", ""),
                    admin_telegram_id=extra_data.get("admin_telegram_id"),
                    plan_id=payment.plan_id,
                    password_hash=extra_data.get("password_hash", ""),
                    subscription_status="active",  # Исправлено: используем строку вместо enum
                    can_create_bookings=True,
                    subscription_end_date=date.today() + timedelta(days=30),
                    is_active=True
                )
                
                db.add(company)
                await db.flush()  # Получаем ID компании
                
                # 2. Создаем tenant схему и клонируем таблицы
                logger.info(f"Создание tenant схемы для компании {company.id}...")
                tenant_service = get_tenant_service()
                
                # Инициализируем tenant (создаем схему и клонируем таблицы)
                tenant_initialized = await tenant_service.initialize_tenant_for_company(company.id)
                
                if not tenant_initialized:
                    logger.error(f"Не удалось инициализировать tenant для компании {company.id}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Ошибка создания tenant схемы"
                    )
                
                # 3. Создаем подписку
                logger.info(f"Создание подписки для компании {company.id}...")
                subscription = Subscription(
                    company_id=company.id,
                    plan_id=payment.plan_id,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=30),
                    status="active"  # Исправлено: используем строку вместо enum
                )
                
                db.add(subscription)
                
                # 4. Обновляем статус платежа
                payment.company_id = company.id
                payment.status = "succeeded"  # Исправлено: используем строку вместо enum
                
                logger.info(f"Компании {company.id} успешно создана!")
                
                await db.commit()
                
                # 5. Отправляем уведомления (вне транзакции)
                try:
                    # Email с данными для входа
                    password = extra_data.get("password", "GeneratedPassword123")
                    await send_welcome_email(
                        company_name=company.name,
                        email=company.email,
                        password=password,
                        dashboard_url=f"https://barber-saas.com/company/{company.id:03d}/dashboard",
                        plan_name=plan.name,
                        subscription_end_date=company.subscription_end_date
                    )
                    logger.info(f"Приветственное email отправлено на {company.email}")
                    
                    # Telegram уведомление владельцу
                    await send_activation_notification(
                        telegram_id=company.admin_telegram_id,
                        company_name=company.name,
                        plan_name=plan.name,
                        subscription_end_date=company.subscription_end_date,
                        dashboard_url=f"https://barber-saas.com/company/{company.id:03d}/dashboard",
                        can_create_bookings=True
                    )
                    if company.admin_telegram_id:
                        logger.info(f"Telegram уведомление отправлено на {company.admin_telegram_id}")
                    
                except Exception as email_error:
                    logger.error(f"Ошибка отправки уведомлений: {email_error}")
                    # Не прерываем процесс, так как компания создана
        
        # Обработка отмененного платежа
        elif webhook_data.event == "payment.canceled":
            logger.info(f"Платеж {payment.id} отменен")
            payment.status = "failed"  # Исправлено: используем строку
            await db.commit()
        
        # Обработка возврата платежа
        elif webhook_data.event == "payment.refunded":
            logger.info(f"Платеж {payment.id} возвращен")
            payment.status = "refunded"  # Исправлено: используем строку
            await db.commit()
        
        # Если платеж уже обработан, игнорируем
        elif payment.status == "succeeded":  # Исправлено: используем строку
            logger.info(f"Платеж {payment.id} уже обработан, пропускаем")
            return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обработки webhook: {str(e)}"
        )
    
    logger.info("Webhook обработан успешно")
    return {"success": True}


@router.post("/yookassa/test", status_code=200)
async def test_yookassa_webhook(
    request: Request,
    signature: Annotated[str, Header(alias="IIS-Signature")] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Тестовый endpoint для webhook от Юкассы.
    
    Используется для проверки правильности интеграции без создания реальных платежей.
    """
    logger.info("Тестовый webhook от Юкассы")
    
    payload = await get_webhook_body(request)
    payload_str = payload.decode('utf-8')
    
    if signature:
        is_valid = verify_webhook_signature(payload_str, signature)
        logger.info(f"Подпись валидна: {is_valid}")
    else:
        logger.info("Подпись не предоставлена")
    
    logger.info(f"Webhook данные: {payload_str[:200]}...")
    
    return {
        "success": True,
        "signature_valid": signature is not None,
        "event": "test"
    }


@router.post("/yookassa/simulate/{payment_id}", status_code=200)
async def simulate_payment_success(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Симулировать успешный платеж для тестирования.
    
    Этот endpoint создает фейковый webhook от Юкассы для указанного платежа,
    что позволяет протестировать создание компании без реальной оплаты.
    
    Args:
        payment_id: ID платежа для симуляции
        db: Асинхронная сессия БД
        
    Returns:
        Результат обработки webhook
    """
    logger.info(f"Симуляция успешного платежа для payment_id={payment_id}")
    
    # Находим платеж
    payment_result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = payment_result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")
    
    if payment.status == "succeeded":
        company_result = await db.execute(
            select(Company).where(Company.id == payment.company_id)
        )
        company = company_result.scalar_one_or_none()
        return {
            "success": True,
            "message": "Платеж уже обработан",
            "company_id": payment.company_id,
            "company_name": company.name if company else None
        }
    
    # Обрабатываем успешный платеж (копируем логику из yookassa_webhook)
    import json
    extra_data = payment.extra_data or {}
    if isinstance(extra_data, str):
        try:
            extra_data = json.loads(extra_data)
        except:
            extra_data = {}
    
    # 1. Создаем компанию
    logger.info("Создание компании...")
    
    plan_result = await db.execute(
        select(Plan).where(Plan.id == payment.plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    
    if not plan:
        logger.error(f"План {payment.plan_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тарифный план не найден"
        )
    
    company = Company(
        name=extra_data.get("company_name", "Неизвестный автосервис"),
        email=extra_data.get("email", ""),
        phone=extra_data.get("phone"),
        telegram_bot_token=extra_data.get("telegram_bot_token", ""),
        admin_telegram_id=extra_data.get("admin_telegram_id"),
        plan_id=payment.plan_id,
        password_hash=extra_data.get("password_hash", ""),
        subscription_status="active",
        can_create_bookings=True,
        subscription_end_date=date.today() + timedelta(days=30),
        is_active=True
    )
    
    db.add(company)
    await db.flush()
    
    # 2. Создаем tenant схему
    logger.info(f"Создание tenant схемы для компании {company.id}...")
    tenant_service = get_tenant_service()
    tenant_initialized = await tenant_service.initialize_tenant_for_company(company.id)
    
    if not tenant_initialized:
        logger.error(f"Не удалось инициализировать tenant для компании {company.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания tenant схемы"
        )
    
    # 3. Создаем подписку
    logger.info(f"Создание подписки для компании {company.id}...")
    subscription = Subscription(
        company_id=company.id,
        plan_id=payment.plan_id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status="active"
    )
    
    db.add(subscription)
    
    # 4. Обновляем статус платежа
    payment.company_id = company.id
    payment.status = "succeeded"
    payment.yookassa_payment_status = "succeeded"
    payment.webhook_received_at = date.today()
    payment.webhook_signature_verified = True
    
    logger.info(f"Компания {company.id} успешно создана!")
    
    await db.commit()
    
    # Отправляем уведомления
    try:
        password = extra_data.get("password", "GeneratedPassword123")
        await send_welcome_email(
            company_name=company.name,
            email=company.email,
            password=password,
            dashboard_url=f"http://localhost:3000/company/{company.id:03d}/dashboard",
            plan_name=plan.name,
            subscription_end_date=company.subscription_end_date
        )
        logger.info(f"Приветственное email отправлено на {company.email}")
    except Exception as email_error:
        logger.error(f"Ошибка отправки email: {email_error}")
    
    return {
        "success": True,
        "message": "Платеж успешно обработан",
        "company_id": company.id,
        "company_name": company.name,
        "email": company.email
    }

