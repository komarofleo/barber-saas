"""
Сервис для отправки Telegram уведомлений.

Этот модуль предоставляет методы для отправки уведомлений
владельцам компаний через Telegram бота.
"""

import logging
from typing import Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Сервис для отправки уведомлений через Telegram API.
    
    Использует API Telegram для отправки сообщений
    пользователям через бота.
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Инициализация сервиса с токеном бота.
        
        Args:
            bot_token: Токен Telegram бота (опционально)
        """
        self.bot_token = bot_token
        self.api_url = "https://api.telegram.org"
        
        if bot_token:
            logger.info(f"TelegramNotificationService инициализирован с токеном: {bot_token[:10]}...")
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Отправить сообщение в Telegram чат.
        
        Args:
            chat_id: ID чата или пользователя
            text: Текст сообщения (поддерживает HTML при parse_mode='HTML')
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
        
        Returns:
            True если сообщение отправлено успешно, False в противном случае
        
        Example:
            >>> await service.send_message(
            ...     chat_id=329621295,
            ...     text="<b>Привет!</b>",
            ...     parse_mode="HTML"
            ... )
        """
        if not self.bot_token:
            logger.error("Токен бота не указан!")
            return False
        
        logger.info(f"Отправка Telegram сообщения в чат {chat_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode
                    }
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    logger.error(f"Ошибка отправки сообщения: {error_data}")
                    return False
                
                result = response.json()
                logger.info(f"Telegram сообщение отправлено успешно: {result.get('message_id')}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP ошибка при отправке сообщения: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram сообщения: {e}")
            return False
    
    async def send_activation_notification(
        self,
        telegram_id: int,
        company_name: str,
        plan_name: str,
        subscription_end_date,
        dashboard_url: str,
        can_create_bookings: bool = True,
        login_email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """
        Отправить уведомление об успешной активации компании.
        
        Args:
            telegram_id: Telegram ID владельца
            company_name: Название салона красоты
            plan_name: Название тарифного плана
            subscription_end_date: Дата окончания подписки
            dashboard_url: Ссылка на админ-панель
            can_create_bookings: Можно ли создавать записи
            login_email: Email для входа (опционально)
            password: Пароль для входа (опционально)
        
        Returns:
            True если уведомление отправлено, False в противном случае
        
        Example:
            >>> await service.send_activation_notification(
            ...     telegram_id=329621295,
            ...     company_name="ООО 'Точка'",
            ...     plan_name="Business",
            ...     subscription_end_date=date(2024, 2, 5),
            ...     dashboard_url="https://barber-saas.com/company/001/dashboard"
            ... )
        """
        logger.info(f"Отправка уведомления об активации: {company_name}")
        
        credentials_block = ""
        if login_email and password:
            credentials_block = f"""
<b>🔐 Данные для входа</b>
<b>Email:</b> {login_email}
<b>Пароль:</b> <code>{password}</code>

<i>Рекомендуем сменить пароль после первого входа.</i>
"""

        message = f"""
        <b>✅ Ваш салон красоты успешно зарегистрирован!</b>

<b>📋 Название:</b> {company_name}

<b>💰 Тарифный план:</b> {plan_name}

<b>📅 Дата окончания подписки:</b> {subscription_end_date.strftime('%d.%m.%Y')}

<b>📚 Создание записей:</b> {'✅ Разрешено' if can_create_bookings else '❌ Заблокировано'}

<b>🔗 Админ-панель:</b>
<a href="{dashboard_url}">{dashboard_url}</a>

{credentials_block}

<b>ℹ️ Для начала работы:</b>
1. Перейдите в админ-панель
2. Создайте услуги и мастеров
3. Настройте рабочее время
4. Настройте слоты для записи
        """
        
        return await self.send_message(telegram_id, message)
    
    async def send_payment_reminder(
        self,
        telegram_id: int,
        company_name: str,
        days_left: int,
        dashboard_url: str
    ) -> bool:
        """
        Отправить напоминание о скором окончании подписки.
        
        Args:
            telegram_id: Telegram ID владельца
            company_name: Название салона красоты
            days_left: Дней до окончания подписки
            dashboard_url: Ссылка на админ-панель
        
        Returns:
            True если напоминание отправлено, False в противном случае
        
        Example:
            >>> await service.send_payment_reminder(
            ...     telegram_id=329621295,
            ...     company_name="ООО 'Точка'",
            ...     days_left=7,
            ...     dashboard_url="https://barber-saas.com/company/001/dashboard"
            ... )
        """
        logger.info(f"Отправка напоминания: {company_name}, осталось {days_left} дней")
        
        message = f"""
        <b>⚠️ Внимание!</b>

Подписка салона красоты <b>{company_name}</b> истекает через <b>{days_left} дней</b>.

Для продления подписки:
<a href="{dashboard_url}">Перейти в админ-панель</a>

📅 Дата окончания: {(date.today() + timedelta(days=days_left)).strftime('%d.%m.%Y')}
        """
        
        return await self.send_message(telegram_id, message)
    
    async def send_booking_blocked_notification(
        self,
        telegram_id: int,
        company_name: str,
        dashboard_url: str
    ) -> bool:
        """
        Отправить уведомление о блокировке создания записей.
        
        Args:
            telegram_id: Telegram ID владельца
            company_name: Название салона красоты
            dashboard_url: Ссылка на админ-панель
        
        Returns:
            True если уведомление отправлено, False в противном случае
        
        Example:
            >>> await service.send_booking_blocked_notification(
            ...     telegram_id=329621295,
            ...     company_name="ООО 'Точка'",
            ...     dashboard_url="https://barber-saas.com/company/001/dashboard"
            ... )
        """
        logger.warning(f"Отправка уведомления о блокировке: {company_name}")
        
        message = f"""
        <b>❌ Создание записей заблокировано!</b>

Подписка салона красоты <b>{company_name}</b> истекла.

Для возобновления возможности создания записей:
<a href="{dashboard_url}">Продлите подписку</a>

💰 После продления подписки создание записей будет разблокировано автоматически.
        """
        
        return await self.send_message(telegram_id, message)
    
    async def send_payment_success_notification(
        self,
        telegram_id: int,
        company_name: str,
        amount: float,
        subscription_end_date
    ) -> bool:
        """
        Отправить уведомление об успешной оплате.
        
        Args:
            telegram_id: Telegram ID владельца
            company_name: Название салона красоты
            amount: Сумма платежа
            subscription_end_date: Дата окончания подписки
        
        Returns:
            True если уведомление отправлено, False в противном случае
        """
        logger.info(f"Отправка уведомления об оплате: {company_name}, {amount} RUB")
        
        message = f"""
        <b>💳 Платеж принят!</b>

Подписка салона красоты <b>{company_name}</b> успешно продлена на 30 дней.

<b>💰 Сумма:</b> {amount:.2f} RUB
<b>📅 Дата окончания:</b> {subscription_end_date.strftime('%d.%m.%Y')}

Спасибо за использование Barber SaaS! 💇
        """
        
        return await self.send_message(telegram_id, message)


# Создание экземпляра сервиса (singleton)
_telegram_notification_service: Optional[TelegramNotificationService] = None


def get_telegram_notification_service(bot_token: Optional[str] = None) -> TelegramNotificationService:
    """
    Получить или создать экземпляр TelegramNotificationService.
    
    Args:
        bot_token: Токен Telegram бота (опционально)
    
    Returns:
        Экземпляр TelegramNotificationService
    """
    global _telegram_notification_service
    
    if _telegram_notification_service is None:
        resolved_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        _telegram_notification_service = TelegramNotificationService(resolved_token)
    
    return _telegram_notification_service


async def send_activation_notification(
    telegram_id: int,
    company_name: str,
    plan_name: str,
    subscription_end_date,
    dashboard_url: str,
    can_create_bookings: bool = True,
    login_email: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    """
    Удобная функция для отправки уведомления об активации.
    
    Args:
        telegram_id: Telegram ID владельца
        company_name: Название автосервиса
        plan_name: Название тарифного плана
        subscription_end_date: Дата окончания подписки
        dashboard_url: Ссылка на админ-панель
        can_create_bookings: Можно ли создавать записи
    
    Returns:
        True если уведомление отправлено, False в противном случае
    """
    service = get_telegram_notification_service()
    return await service.send_activation_notification(
        telegram_id,
        company_name,
        plan_name,
        subscription_end_date,
        dashboard_url,
        can_create_bookings,
        login_email,
        password,
    )

