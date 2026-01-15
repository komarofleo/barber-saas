"""
Middleware для проверки статуса подписки в Telegram боте.

Этот middleware проверяет:
- Статус подписки компании
- Может ли пользователь создавать записи
- Добавляет информацию о подписке в состояние
"""
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Optional, Callable, Awaitable, Any

from app.config import settings

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware для проверки статуса подписки.
    
    Добавляет в event следующие данные:
    - can_create_bookings: bool - может ли создавать записи
    - subscription_status: str - статус подписки
    - subscription_end_date: datetime или None - дата окончания
    - company_id: int - ID компании
    - company_name: str - название компании
    """
    
    async def __call__(
        self,
        handler: Callable[[Any], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict,
    ) -> Any:
        """
        Проверяет статус подписки перед выполнением хендлера.
        
        Args:
            handler: Telegram хендлер
            event: Telegram событие
            data: Данные события
            
        Returns:
            Результат хендлера или None если заблокирован
        """
        # Логируем все сообщения для отладки
        if isinstance(event, Message) and event.text:
            handler_name = getattr(handler, '__name__', str(handler))
            # Получаем имя функции-обработчика, если это функция
            if hasattr(handler, '__name__'):
                handler_name = handler.__name__
            elif hasattr(handler, 'callback') and hasattr(handler.callback, '__name__'):
                handler_name = handler.callback.__name__
            logger.info(f"🔵 [MIDDLEWARE] Сообщение: text='{event.text}', from_user={event.from_user.id}, handler={handler_name}")
            import sys
            print(f"🔵 [MIDDLEWARE] Сообщение: text='{event.text}', from_user={event.from_user.id}, handler={handler_name}", file=sys.stderr, flush=True)
            
            # Если это сообщение "📋 Новые заказы", логируем дополнительно
            if event.text == "📋 Новые заказы":
                logger.info(f"🔵🔵🔵 [MIDDLEWARE] НАЙДЕНО СООБЩЕНИЕ '📋 Новые заказы'! handler={handler_name}")
                print(f"🔵🔵🔵 [MIDDLEWARE] НАЙДЕНО СООБЩЕНИЕ '📋 Новые заказы'! handler={handler_name}", file=sys.stderr, flush=True)
        # Получаем диспетчер через event
        dispatcher = None
        try:
            # В aiogram 3.x диспетчер доступен через event.bot.session
            # Но проще получить через data['dispatcher'] если он там есть
            if 'dispatcher' in data:
                dispatcher = data['dispatcher']
            else:
                # Пробуем получить через event.bot
                bot = event.bot
                # В aiogram 3.x диспетчер хранится в bot.session
                if hasattr(bot, 'session') and hasattr(bot.session, 'dispatcher'):
                    dispatcher = bot.session.dispatcher
        except:
            pass
        
        # Если не удалось получить диспетчер, пробуем получить данные из data
        if not dispatcher:
            # Используем данные из data, если они там есть
            can_create_bookings = data.get('can_create_bookings', True)
            subscription_status = data.get('subscription_status', 'no_subscription')
            subscription_end_date = data.get('subscription_end_date', None)
            company_id = data.get('company_id', None)
            company_name = data.get('company_name', 'Unknown')
        else:
            # Получаем данные о подписке из контекста диспетчера
            can_create_bookings = dispatcher.get('can_create_bookings', True) if hasattr(dispatcher, 'get') else True
            subscription_status = dispatcher.get('subscription_status', 'no_subscription') if hasattr(dispatcher, 'get') else 'no_subscription'
            subscription_end_date = dispatcher.get('subscription_end_date', None) if hasattr(dispatcher, 'get') else None
            company_id = dispatcher.get('company_id', None) if hasattr(dispatcher, 'get') else None
            company_name = dispatcher.get('company_name', 'Unknown') if hasattr(dispatcher, 'get') else 'Unknown'
        
        # Добавляем company_id в data для использования в хендлерах
        data['company_id'] = company_id
        data['can_create_bookings'] = can_create_bookings
        data['subscription_status'] = subscription_status
        
        # Добавляем диспетчер в data, если он найден
        if dispatcher:
            data['dispatcher'] = dispatcher
        
        # Проверяем подписку только для команд, связанных с созданием записей
        command = event.text if isinstance(event, Message) and event.text else None
        
        # Список команд, требующих активной подписки
        booking_commands = ['/start', 'Записаться', 'Запись']
        
        # Проверяем, нужно ли блокировать эту команду
        should_block = False
        if command:
            for booking_cmd in booking_commands:
                if booking_cmd in command and not can_create_bookings:
                    should_block = True
                    break
        
        if should_block:
            # Логируем блокировку
            logger.warning(
                f"Подписка истекла для компании '{company_name}' (ID: {company_id}). "
                f"Статус подписки: {subscription_status}, "
                f"Дата окончания: {subscription_end_date}"
            )
            
            # Отправляем сообщение об истекшей подписке
            if isinstance(event, Message):
                await event.answer(
                    f"⚠️ **Подписка истекла**\n\n"
                    f"Ваша подписка компании '{company_name}' истекла.\n"
                    f"Пожалуйста, продлите подписку для создания записей.\n\n"
                    f"Для продления подписки обратитесь к администратору."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Подписка истекла. Создание записей заблокировано.",
                    show_alert=True
                )
            
            return None
        
        # Если подписка истекает через 7 дней или меньше - отправляем предупреждение
        if subscription_end_date:
            from datetime import datetime, date, timedelta
            
            days_left = (subscription_end_date - date.today()).days
            
            if days_left <= 7 and days_left > 0 and command and 'Запис' in command:
                logger.info(
                    f"Подписка истекает для компании '{company_name}' (ID: {company_id}). "
                    f"Осталось {days_left} дней."
                )
                
                if isinstance(event, Message):
                    await event.answer(
                        f"⚠️ **Подписка истекает через {days_left} дней!**\n\n"
                        f"Пожалуйста, продлите подписку для продолжения работы."
                    )
        
        # Логирование успешной проверки
        if company_id:
            logger.info(
                f"SubscriptionMiddleware: company_id={company_id}, "
                f"company_name={company_name}, "
                f"status={subscription_status}, "
                f"can_create_bookings={can_create_bookings}"
            )
        
        # Продолжаем выполнение хендлера
        return await handler(event, data)

