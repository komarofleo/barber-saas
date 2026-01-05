"""
Сервис для интеграции с платежной системой Юкасса.

Этот модуль предоставляет методы для создания платежей, проверки их статуса
и верификации подписей webhook от Юкассы.
"""

import hashlib
import hmac
import logging
import httpx
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from web.backend.app.config import settings

logger = logging.getLogger(__name__)


class YooKassaService:
    """
    Сервис для работы с платежной системой Юкасса.
    
    Предоставляет методы для:
    - Создания платежей
    - Получения информации о платежах
    - Проверки подписей webhook
    """
    
    def __init__(self):
        """Инициализация сервиса с конфигурацией."""
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.api_url = settings.YOOKASSA_API_URL or "https://api.yookassa.ru/v3"
        
        logger.info(f"YooKassaService инициализирован: shop_id={self.shop_id}")
    
    async def create_payment(
        self,
        amount: Decimal,
        description: str,
        return_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Создать платеж через Юкассу.
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            return_url: URL для перенаправления после оплаты
            metadata: Метаданные платежа (словарь)
        
        Returns:
            Словарь с данными созданного платежа:
            - id: ID платежа в Юкасса
            - confirmation_url: Ссылка для оплаты
            - created_at: Дата создания
        
        Raises:
            HTTPException: При ошибке создания платежа
        
        Example:
            >>> payment = await yookassa.create_payment(
            ...     amount=Decimal("5000.00"),
            ...     description="Подписка на тариф Business",
            ...     return_url="https://mysite.com/success"
            ... )
        """
        logger.info(f"Создание платежа: {description}, сумма: {amount} RUB")
        
        # Формируем данные для запроса
        payment_data = {
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "description": description,
            "capture": True,  # Автоматическое списание
            "metadata": metadata or {}
        }
        
        # Добавляем URL возврата если указан
        if return_url:
            payment_data["confirmation"] = {
                "type": "redirect",
                "return_url": return_url
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/payments",
                    json=payment_data,
                    auth=(self.shop_id, self.secret_key),
                    headers={
                        "Idempotence-Key": str(datetime.utcnow().timestamp()),
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    logger.error(f"Ошибка создания платежа: {error_data}")
                    raise Exception(
                        f"Ошибка создания платежа: {error_data.get('description', 'Неизвестная ошибка')}"
                    )
                
                payment = response.json()
                logger.info(f"Платеж создан успешно: {payment['id']}")
                
                return {
                    "id": payment["id"],
                    "confirmation_url": payment.get("confirmation", {}).get("confirmation_url"),
                    "created_at": payment.get("created_at"),
                    "status": payment.get("status"),
                    "amount": payment["amount"]["value"],
                    "currency": payment["amount"]["currency"],
                    "description": payment.get("description"),
                    "metadata": payment.get("metadata")
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP ошибка при создании платежа: {e}")
            raise Exception(f"Ошибка соединения с Юкассой: {str(e)}")
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Получить информацию о платеже по его ID.
        
        Args:
            payment_id: ID платежа в Юкасса
        
        Returns:
            Словарь с данными платежа:
            - id: ID платежа
            - status: Статус платежа
            - amount: Сумма платежа
            - created_at: Дата создания
            - paid_at: Дата оплаты (если оплачен)
        
        Example:
            >>> payment = await yookassa.get_payment("12345")
        """
        logger.info(f"Получение информации о платеже: {payment_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/payments/{payment_id}",
                    auth=(self.shop_id, self.secret_key)
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    logger.error(f"Ошибка получения платежа: {error_data}")
                    raise Exception(
                        f"Ошибка получения платежа: {error_data.get('description', 'Неизвестная ошибка')}"
                    )
                
                payment = response.json()
                logger.info(f"Платеж получен: {payment['id']}, статус: {payment['status']}")
                
                return payment
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP ошибка при получении платежа: {e}")
            raise Exception(f"Ошибка соединения с Юкассой: {str(e)}")
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Проверить подпись webhook от Юкассы.
        
        Args:
            payload: Тело запроса webhook в виде строки
            signature: Заголовок IIS-Signature
        
        Returns:
            True если подпись валидна, False в противном случае
        
        Example:
            >>> is_valid = yookassa.verify_webhook_signature(
            ...     payload='{"event":"payment.succeeded","object":{"id":"12345"}}',
            ...     signature="aBc123..."
            ... )
        """
        try:
            # Создаем HMAC-SHA256 хэш из payload с секретным ключом
            digest = hmac.new(
                self.secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Сравниваем хэши с подписью (защита от timing attacks)
            is_valid = hmac.compare_digest(digest, signature)
            
            if is_valid:
                logger.info("Подпись webhook верифицирована успешно")
            else:
                logger.warning("Подпись webhook не валидна!")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Ошибка проверки подписи webhook: {e}")
            return False
    
    async def get_payment_status(self, payment_id: str) -> str:
        """
        Получить статус платежа в понятном формате.
        
        Args:
            payment_id: ID платежа в Юкасса
        
        Returns:
            Статус платежа:
            - pending: Ожидает оплаты
            - waiting_for_capture: Ожидает списания
            - succeeded: Оплачен успешно
            - canceled: Отменен
            - refunded: Возвращен
        
        Example:
            >>> status = await yookassa.get_payment_status("12345")
            >>> print(status)  # "succeeded"
        """
        payment = await self.get_payment(payment_id)
        return payment.get("status", "unknown")
    
    def is_payment_successful(self, status: str) -> bool:
        """
        Проверить, является ли платеж успешным.
        
        Args:
            status: Статус платежа
        
        Returns:
            True если платеж успешен, False в противном случае
        """
        return status == "succeeded"
    
    def is_payment_failed(self, status: str) -> bool:
        """
        Проверить, является ли платеж неудачным.
        
        Args:
            status: Статус платежа
        
        Returns:
            True если платеж неудачен, False в противном случае
        """
        return status in ["canceled", "refunded"]
    
    def is_payment_pending(self, status: str) -> bool:
        """
        Проверить, ожидает ли платеж оплаты.
        
        Args:
            status: Статус платежа
        
        Returns:
            True если платеж ожидает оплаты, False в противном случае
        """
        return status in ["pending", "waiting_for_capture"]


# Создание экземпляра сервиса (singleton)
_yookassa_service: Optional[YooKassaService] = None


def get_yookassa_service() -> YooKassaService:
    """
    Получить или создать экземпляр YooKassaService.
    
    Returns:
        Экземпляр YooKassaService
    """
    global _yookassa_service
    
    if _yookassa_service is None:
        _yookassa_service = YooKassaService()
    
    return _yookassa_service


async def create_payment(
    amount: Decimal,
    description: str,
    return_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Удобная функция для создания платежа.
    
    Args:
        amount: Сумма платежа
        description: Описание платежа
        return_url: URL для перенаправления после оплаты
        metadata: Метаданные платежа
    
    Returns:
        Словарь с данными созданного платежа
    """
    service = get_yookassa_service()
    return await service.create_payment(amount, description, return_url, metadata)


async def get_payment(payment_id: str) -> Dict[str, Any]:
    """
    Удобная функция для получения информации о платеже.
    
    Args:
        payment_id: ID платежа в Юкасса
    
    Returns:
        Словарь с данными платежа
    """
    service = get_yookassa_service()
    return await service.get_payment(payment_id)


def verify_webhook_signature(payload: str, signature: str) -> bool:
    """
    Удобная функция для проверки подписи webhook.
    
    Args:
        payload: Тело запроса webhook в виде строки
        signature: Заголовок IIS-Signature
    
    Returns:
        True если подпись валидна, False в противном случае
    """
    service = get_yookassa_service()
    return service.verify_webhook_signature(payload, signature)

