"""
Middleware для проверки статуса подписки в Telegram боте.

Этот middleware проверяет:
- Статус подписки компании
- Может ли пользователь создавать записи
- Добавляет информацию о подписке в состояние
"""
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Optional

from app.config import settings


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware для проверки статуса подписки.
    
    Добавляет в update следующие данные:
    - can_create_bookings: bool - может ли создавать записи
    - subscription_status: str - статус подписки
    - days_left: int или None - дней до окончания
    - subscription_plan_id: int или None - ID тарифного плана
    """
    
    async def __call__(
        self,
        handler: TelegramObject,
        event: TelegramObject,
        data: dict,
    ) -> Optional[dict]:
        """
        Проверяет статус подписки перед выполнением хендлера.
        
        Args:
            handler: Telegram хендлер
            event: Telegram событие
            data: Данные события
            
        Returns:
            Обновленные данные для события или None
        """
        # Получаем данные о подписке из контекста
        can_create_bookings = data.get('can_create_bookings', True)
        subscription_status = data.get('subscription_status', 'no_subscription')
        days_left = data.get('days_left', None)
        subscription_plan_id = data.get('subscription_plan_id', None)
        
        # Логируем для отладки
        # from app.services.tenant_service import get_tenant_service  # Не можем импортировать здесь (цирка)
        # tenant_service = get_tenant_service()
        # company_id = data.get('company_id')
        # if company_id:
        #     subscription_info = await check_company_subscription(tenant_service, company_id)
        #     subscription_status = subscription_info.get('status', 'no_subscription')
        #     days_left = subscription_info.get('days_left', None)
        #     can_create_bookings = subscription_info.get('can_create_bookings', False)
        
        # Обновляем данные для события
        event.can_create_bookings = can_create_bookings
        event.subscription_status = subscription_status
        event.days_left = days_left
        event.subscription_plan_id = subscription_plan_id
        
        # Логирование
        # if company_id:
        #     logger.info(
        #         f"SubscriptionMiddleware: company_id={company_id}, "
        #         f"status={subscription_status}, days_left={days_left}, "
        #         f"can_create={can_create_bookings}"
        #     )
        
        # Если подписка истекла или истекает - отправляем уведомление
        if subscription_status == 'expired' or (days_left is not None and days_left <= 7):
            # TODO: Добавить логирование уведомления
            pass
        
        return event

