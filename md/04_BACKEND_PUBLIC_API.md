# Этап 4: Backend - Публичные API

**Продолжительность:** 2 дня  
**Статус:** ⏳ В ожидании  
**Приоритет:** Критический

---

## 📋 Содержание

1. [Цель этапа](#цель-этапа)
2. [Предварительные требования](#предварительные-требования)
3. [Подзадачи](#подзадачи)
4. [Чек-лист этапа](#чек-лист-этапа)
5. [Риски и их решение](#риски-и-их-решение)

---

## 🎯 Цель этапа

Реализовать публичные API для регистрации новых клиентов без авторизации.

### Ожидаемый результат

- Публичные API endpoints работают
- Валидация токена бота работает
- Регистрация новой компании работает
- Интеграция с Юкассой работает
- Webhook от Юкассы обрабатывается
- Автоматическое создание схемы после оплаты

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Этап 2 завершен (модели и схемы созданы)
- [ ] Этап 3 завершен (мульти-тенантность работает)
- [ ] Есть тестовый магазин Юкассы
- [ ] Понимание работы с webhook

### Технические требования

- Python 3.11+ установлен
- aiohttp установлен
- Тестовый магазин Юкассы доступен
- Понимание работы с API Telegram и Юкассы

---

## 📝 Подзадачи

### Подзадача 4.1: Создать публичный API модуль

**Описание:** Создать новый модуль для публичных API.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/api/public.py
   ```

2. Определить роутер:
   ```python
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel, Field

   router = APIRouter(prefix="/api/public", tags=["public"])
   ```

**Критерии выполнения:**
- [ ] Модуль создан
- [ ] Роутер определен
- [ ] Префикс /api/public
- [ ] Импортируется без ошибок

---

### Подзадача 4.2: Реализовать валидацию токена бота

**Описание:** Создать endpoint для проверки валидности токена бота через Telegram API.

**Что нужно сделать:**

1. Определить Pydantic схему:
   ```python
   class ValidateBotTokenRequest(BaseModel):
       token: str = Field(..., min_length=50, max_length=500, description="Токен бота от @BotFather")
   
   class ValidateBotTokenResponse(BaseModel):
       valid: bool
       bot_info: Optional[dict]
       error: Optional[str]
   ```

2. Реализовать endpoint:
   ```python
   import aiohttp
   import logging
   
   logger = logging.getLogger(__name__)
   
   @router.post("/validate-bot-token", response_model=ValidateBotTokenResponse)
   async def validate_bot_token(request: ValidateBotTokenRequest):
       """Проверка валидности токена бота через Telegram API"""
       try:
           # Проверяем токен через Telegram API
           async with aiohttp.ClientSession() as session:
               url = f"https://api.telegram.org/bot{request.token}/getMe"
               async with session.get(url) as response:
                   data = await response.json()
                   
                   if not data.get("ok"):
                       return ValidateBotTokenResponse(
                           valid=False,
                           error=data.get("description", "Неизвестная ошибка")
                       )
                   
                   bot_info = data["result"]
                   
                   # Проверяем, что это бот
                   if not bot_info.get("is_bot"):
                       return ValidateBotTokenResponse(
                           valid=False,
                           error="Этот токен не принадлежит боту"
                       )
                   
                   return ValidateBotTokenResponse(
                       valid=True,
                       bot_info=bot_info
                   )
       
       except aiohttp.ClientError as e:
           logger.error(f"Ошибка при проверке токена: {e}")
           return ValidateBotTokenResponse(
               valid=False,
               error="Не удалось подключиться к Telegram API"
           )
       except Exception as e:
           logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
           return ValidateBotTokenResponse(
               valid=False,
               error="Внутренняя ошибка сервера"
           )
   ```

**Критерии выполнения:**
- [ ] Endpoint создан
- [ ] Валидация через Telegram API работает
- [ ] Проверка is_bot работает
- [ ] Обработка ошибок работает
- [ ] Логирование работает

---

### Подзадача 4.3: Создать YooKassa сервис

**Описание:** Создать сервис для интеграции с Юкассой.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/services/yookassa_service.py
   ```

2. Определить сервис:
   ```python
   from typing import Optional, Dict, Any
   from decimal import Decimal
   import aiohttp
   import hmac
   import hashlib
   import base64
   import logging
   
   from app.config import settings
   
   logger = logging.getLogger(__name__)
   
   class YooKassaService:
       """Сервис для работы с Юкассой"""
       
       def __init__(self):
           # Получаем настройки из env
           self.shop_id = getattr(settings, 'YOOKASSA_SHOP_ID', '')
           self.secret_key = getattr(settings, 'YOOKASSA_SECRET_KEY', '')
           self.api_url = getattr(settings, 'YOOKASSA_API_URL', 'https://api.yookassa.ru/v3/payments')
       
       async def create_payment(
           self,
           amount: Decimal,
           description: str,
           metadata: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Создание платежа"""
           try:
               payload = {
                   "amount": {
                       "value": str(amount),
                       "currency": "RUB"
                   },
                   "description": description,
                   "metadata": metadata,
                   "capture": True,  # Списание сразу
                   "confirmation": {
                       "type": "redirect",
                       "return_url": f"{getattr(settings, 'FRONTEND_URL', '')}/payment-success"
                   }
               }
               
               # Аутентификация через Basic Auth
               auth = aiohttp.BasicAuth(
                   self.shop_id,
                   self.secret_key
               )
               
               async with aiohttp.ClientSession() as session:
                   async with session.post(
                       self.api_url,
                       json=payload,
                       auth=auth
                   ) as response:
                       data = await response.json()
                       
                       if response.status != 200:
                           logger.error(f"Ошибка создания платежа: {data}")
                           raise Exception(f"Ошибка Юкассы: {data.get('message', 'Неизвестная ошибка')}")
                       
                       return data
       
       async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
           """Получение информации о платеже"""
           try:
               auth = aiohttp.BasicAuth(
                   self.shop_id,
                   self.secret_key
               )
               
               url = f"{self.api_url}/{payment_id}"
               
               async with aiohttp.ClientSession() as session:
                   async with session.get(url, auth=auth) as response:
                       data = await response.json()
                       
                       return data
       
           except Exception as e:
               logger.error(f"Ошибка получения платежа: {e}")
               return None
       
       def verify_webhook_signature(self, payload: str, signature: str) -> bool:
           """Проверка подписи webhook"""
           # HMAC SHA256 проверка
           hmac_obj = hmac.new(
               self.secret_key.encode('utf-8'),
               payload.encode('utf-8'),
               hashlib.sha256
           )
           digest = hmac_obj.digest()
           calculated_signature = base64.b64encode(digest).decode('utf-8')
           
           return calculated_signature == signature
   ```

**Критерии выполнения:**
- [ ] YooKassaService создан
- [ ] create_payment работает
- [ ] get_payment работает
- [ ] verify_webhook_signature работает
- [ ] Обработка ошибок работает

---

### Подзадача 4.4: Реализовать создание платежа

**Описание:** Создать endpoint для создания платежа при регистрации компании.

**Что нужно сделать:**

1. Определить Pydantic схемы:
   ```python
   class CreatePaymentRequest(BaseModel):
       plan_id: int = Field(..., ge=1, description="ID тарифного плана")
       company_data: CompanyCreate
       
       class Config:
           from_attributes = True
   
   class CreatePaymentResponse(BaseModel):
       payment_url: str
       payment_id: str
       amount: Decimal
       currency: str
       status: str
   ```

2. Реализовать endpoint:
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from decimal import Decimal
   
   from app.database import get_session_with_schema
   from app.models.company import Company
   from app.models.plan import Plan
   from app.models.payment import Payment
   from app.schemas.company import CompanyCreate, CompanyResponse
   from app.services.company_service import create_company
   from app.services.payment_service import create_payment
   from app.services.yookassa_service import YooKassaService
   from app.services.tenant_service import TenantService
   
   @router.post("/create-payment", response_model=CreatePaymentResponse)
   async def create_payment_registration(
       request: CreatePaymentRequest,
       db: AsyncSession = Depends(get_db)
   ):
       """Создание платежа для регистрации компании"""
       try:
           # 1. Проверяем план
           plan_result = await db.execute(
               select(Plan).where(Plan.id == request.plan_id)
           )
           plan = plan_result.scalar_one_or_none()
           
           if not plan:
               raise HTTPException(
                   status_code=404,
                   detail=f"Тарифный план с ID {request.plan_id} не найден"
               )
           
           # 2. Проверяем, существует ли компания с таким кодом
           existing_company = await db.execute(
               select(Company).where(Company.code == request.company_data.code)
           ).scalar_one_or_none()
           
           if existing_company:
               raise HTTPException(
                   status_code=400,
                   detail="Компания с таким кодом уже существует"
               )
           
           # 3. Создаем компанию со статусом pending
           company_data = request.company_data.model_dump()
           company_data['is_active'] = False  # Не активна до оплаты
           company_data['subscription_status'] = 'pending'
           company_data['subscription_end_date'] = None
           company_data['can_create_bookings'] = False
           
           company = await create_company(db, company_data)
           
           # 4. Создаем платеж через Юкассу
           yookassa = YooKassaService()
           
           payment_result = await yookassa.create_payment(
               amount=Decimal(str(plan.price_monthly)),
               description=f"Подписка на тариф {plan.name}",
               metadata={
                   "company_id": company.id,
                   "plan_id": plan.id,
                   "company_name": company.name
               }
           )
           
           # 5. Сохраняем информацию о платеже
           payment_data = {
               "company_id": company.id,
               "amount": Decimal(str(payment_result['amount']['value'])),
               "currency": payment_result['amount']['currency'],
               "payment_method": "yookassa",
               "yookassa_payment_id": payment_result['id'],
               "yookassa_payment_status": payment_result['status'],
               "status": "pending",
               "metadata": {
                   "plan_id": plan.id,
                   "company_name": company.name
               }
           }
           
           payment = await create_payment(db, payment_data)
           
           return CreatePaymentResponse(
               payment_url=payment_result['confirmation']['confirmation_url'],
               payment_id=payment_result['id'],
               amount=Decimal(str(payment_result['amount']['value'])),
               currency=payment_result['amount']['currency'],
               status=payment_result['status']
           )
       
       except HTTPException:
           raise
       except Exception as e:
           logger.error(f"Ошибка создания платежа: {e}", exc_info=True)
           raise HTTPException(
               status_code=500,
               detail="Ошибка при создании платежа"
           )
   ```

**Критерии выполнения:**
- [ ] Endpoint создан
- [ ] Создание компании работает
- [ ] Создание платежа через Юкассу работает
- [ ] Сохранение платежа работает
- [ ] Ошибки обрабатываются

---

### Подзадача 4.5: Реализовать регистрацию компании

**Описание:** Создать полный endpoint регистрации компании с созданием платежа.

**Что нужно сделать:**

1. Объединить логику создания платежа и регистрации:
   ```python
   @router.post("/companies/register", response_model=CreatePaymentResponse)
   async def register_company(
       request: CreatePaymentRequest,
       db: AsyncSession = Depends(get_db)
   ):
       """Регистрация новой компании с созданием платежа"""
       # Логика из подзадачи 4.4
       # ...
   ```

**Критерии выполнения:**
- [ ] Endpoint создан
- [ ] Регистрация работает
- [ ] Платеж создается
- [ ] Возвращается URL оплаты

---

### Подзадача 4.6: Реализовать webhook от Юкассы

**Описание:** Создать endpoint для обработки webhook от Юкассы после успешной оплаты.

**Что нужно сделать:**

1. Определить Pydantic схемы:
   ```python
   class YooKassaWebhook(BaseModel):
       event: str = Field(..., description="Тип события")
       object: Dict[str, Any] = Field(..., description="Объект платежа")
   ```

2. Реализовать endpoint:
   ```python
   from fastapi import BackgroundTasks
   import asyncio
   from datetime import date, timedelta
   
   from app.database import get_session_with_schema
   from app.models.company import Company
   from app.models.subscription import Subscription
   from app.models.payment import Payment
   from app.services.payment_service import update_payment
   from app.services.subscription_service import create_subscription
   from app.services.tenant_service import TenantService
   from app.services.yookassa_service import YooKassaService
   
   @router.post("/payments/yookassa/webhook")
   async def yookassa_webhook(
       webhook_data: YooKassaWebhook,
       background_tasks: BackgroundTasks,
       db: AsyncSession = Depends(get_db)
   ):
       """Обработка webhook от Юкассы"""
       try:
           logger.info(f"Получен webhook: {webhook_data.event}")
           
           # Обрабатываем только успешные платежи
           if webhook_data.event != "payment.succeeded":
               return {"status": "ignored"}
           
           payment_id = webhook_data.object.get("id")
           metadata = webhook_data.object.get("metadata", {})
           
           if not payment_id:
               logger.error("Webhook без payment_id")
               return {"status": "error", "message": "Missing payment_id"}
           
           # Ищем платеж в нашей базе
           payment = await db.execute(
               select(Payment).where(Payment.yookassa_payment_id == payment_id)
           ).scalar_one_or_none()
           
           if not payment:
               logger.error(f"Платеж {payment_id} не найден")
               return {"status": "error", "message": "Payment not found"}
           
           # Если платеж уже обработан
           if payment.status == "completed":
               logger.info(f"Платеж {payment_id} уже обработан")
               return {"status": "already_processed"}
           
           # Обновляем статус платежа
           await update_payment(db, payment.id, {
               "status": "completed",
               "yookassa_payment_status": "succeeded",
               "payment_date": datetime.utcnow()
           })
           
           # Получаем данные компании
           company_id = payment.company_id
           company_result = await db.execute(
               select(Company).where(Company.id == company_id)
           )
           company = company_result.scalar_one_or_none()
           
           if not company:
               logger.error(f"Компания {company_id} не найдена")
               return {"status": "error", "message": "Company not found"}
           
           # Создаем подписку
           plan_id = metadata.get("plan_id")
           start_date = date.today()
           end_date = start_date + timedelta(days=30)  # 1 месяц
           
           subscription = await create_subscription(db, {
               "company_id": company_id,
               "plan_id": plan_id,
               "start_date": start_date,
               "end_date": end_date,
               "status": "active",
               "payment_method": "yookassa"
           })
           
           # Активируем компанию
           company.is_active = True
           company.subscription_status = "active"
           company.subscription_end_date = end_date
           company.can_create_bookings = True
           await db.commit()
           
           # Создаем схему и применяем миграции
           # Это может занять время, поэтому делаем в фоне
           background_tasks.add_task(
               create_company_infrastructure,
               company_id,
               payment_id
           )
           
           logger.info(f"Компания {company_id} успешно активирована")
           
           return {"status": "success"}
       
       except Exception as e:
           logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
           # Не возвращаем ошибку, чтобы Юкасса не повторяла
           return {"status": "error", "message": "Internal server error"}
   
   async def create_company_infrastructure(company_id: int, payment_id: str):
       """Создание инфраструктуры для компании"""
       try:
           # Создаем схему
           schema_name = await TenantService.create_tenant_schema(company_id)
           
           # Применяем миграции
           await TenantService.apply_migrations_to_schema(company_id)
           
           logger.info(f"Инфраструктура для компании {company_id} создана")
       
       except Exception as e:
           logger.error(f"Ошибка создания инфраструктуры: {e}", exc_info=True)
           # Отправляем уведомление супер-админу
           # ...
   ```

3. Добавить webhook в main.py:
   ```python
   from app.api.public import router as public_router
   
   app.include_router(public_router)
   ```

**Критерии выполнения:**
- [ ] Webhook endpoint создан
- [ ] Платеж обновляется
- [ ] Подписка создается
- [ ] Компания активируется
- [ ] Схема создается в фоне
- [ ] Логирование работает

---

### Подзадача 4.7: Добавить переменные окружения для Юкассы

**Описание:** Добавить настройки Юкассы в .env.example.

**Что нужно сделать:**

1. Обновить .env.example:
   ```env
   # ==================== YOOKASSA ====================
   YOOKASSA_SHOP_ID=ваш_shop_id
   YOOKASSA_SECRET_KEY=ваш_secret_key
   YOOKASSA_API_URL=https://api.yookassa.ru/v3/payments
   ```

2. Обновить bot/config.py:
   ```python
   # YooKassa
   YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
   YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
   YOOKASSA_API_URL = os.getenv("YOOKASSA_API_URL", "https://api.yookassa.ru/v3/payments")
   ```

3. Обновить web/backend/app/config.py:
   ```python
   from pydantic_settings import BaseSettings
   
   class Settings(BaseSettings):
       # ... существующие настройки ...
       
       # YooKassa
       YOOKASSA_SHOP_ID: str = ""
       YOOKASSA_SECRET_KEY: str = ""
       YOOKASSA_API_URL: str = "https://api.yookassa.ru/v3/payments"
       
       class Config:
           env_file = ".env"
   
   settings = Settings()
   ```

**Критерии выполнения:**
- [ ] .env.example обновлен
- [ ] bot/config.py обновлен
- [ ] web/backend/app/config.py обновлен
- [ ] Переменные добавлены

---

### Подзадача 4.8: Протестировать интеграцию с Юкассой

**Описание:** Полное тестирование интеграции с тестовым магазином Юкассы.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_yookassa.py
   ```

2. Реализовать тесты:
   ```python
   import asyncio
   from app.services.yookassa_service import YooKassaService
   from decimal import Decimal
   
   async def test_yookassa():
       """Тестирование интеграции с Юкассой"""
       print("=== Тестирование Юкассы ===\n")
       
       yookassa = YooKassaService()
       
       # Тест 1: Создание платежа
       print("1. Создание тестового платежа...")
       try:
           payment = await yookassa.create_payment(
               amount=Decimal("100.00"),
               description="Тестовый платеж",
               metadata={"test": True}
           )
           print(f"✅ Платеж создан: {payment['id']}")
           print(f"   URL: {payment['confirmation']['confirmation_url']}")
           print(f"   Статус: {payment['status']}")
       except Exception as e:
           print(f"❌ Ошибка создания платежа: {e}")
           return
       
       # Тест 2: Получение платежа
       print("\n2. Получение платежа...")
       try:
           payment_id = payment['id']
           payment_info = await yookassa.get_payment(payment_id)
           print(f"✅ Платеж получен: {payment_info}")
       except Exception as e:
           print(f"❌ Ошибка получения платежа: {e}")
       
       # Тест 3: Проверка подписи
       print("\n3. Проверка подписи webhook...")
       payload = '{"test": "payload"}'
       signature = "test_signature"
       is_valid = yookassa.verify_webhook_signature(payload, signature)
       print(f"{'✅ Подпись валидна' if is_valid else '❌ Подпись невалидна'}")
       
       print("\n=== Тестирование завершено ===")
   
   if __name__ == "__main__":
       asyncio.run(test_yookassa())
   ```

3. Запустить тест:
   ```bash
   docker compose exec web python scripts/test_yookassa.py
   ```

**Критерии выполнения:**
- [ ] Тестовый скрипт создан
- [ ] Создание платежа работает
- [ ] Получение платежа работает
- [ ] Проверка подписи работает
- [ ] Все тесты пройдены

---

### Подзадача 4.9: Создать страницу успешной оплаты

**Описание:** Создать endpoint для перенаправления после успешной оплаты.

**Что нужно сделать:**

1. Реализовать endpoint:
   ```python
   @router.get("/payment-success")
   async def payment_success():
       """Страница успешной оплаты"""
       html = """
       <!DOCTYPE html>
       <html>
       <head>
           <title>Оплата успешна</title>
           <style>
               body {
                   font-family: Arial, sans-serif;
                   display: flex;
                   justify-content: center;
                   align-items: center;
                   height: 100vh;
                   margin: 0;
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               }
               .container {
                   text-align: center;
                   color: white;
               }
               h1 {
                   font-size: 48px;
                   margin-bottom: 20px;
               }
               p {
                   font-size: 24px;
                   margin-bottom: 30px;
               }
               button {
                   padding: 15px 30px;
                   font-size: 18px;
                   background: white;
                   color: #667eea;
                   border: none;
                   border-radius: 5px;
                   cursor: pointer;
                   text-decoration: none;
               }
               button:hover {
                   background: #f0f0f0;
               }
           </style>
       </head>
       <body>
           <div class="container">
               <h1>✅</h1>
               <p>Оплата успешна!</p>
               <p>Ваша компания создана и готова к работе.</p>
               <button onclick="window.location.href='/'">Перейти в панель</button>
           </div>
       </body>
       </html>
       """
       return HTMLResponse(content=html)
   ```

**Критерии выполнения:**
- [ ] Endpoint создан
- [ ] HTML страница красивая
- [ ] Перенаправление работает

---

### Подзадача 4.10: Добавить публичные API в main.py

**Описание:** Зарегистрировать публичные API роутеры в главном приложении.

**Что нужно сделать:**

1. Обновить web/backend/main.py:
   ```python
   from app.api.public import router as public_router
   
   # Регистрируем публичные API
   app.include_router(public_router)
   ```

**Критерии выполнения:**
- [ ] Публичные API добавлены
- [ ] Доступны по /api/public/*
- [ ] Работают без авторизации

---

## ✅ Чек-лист этапа

### YooKassa сервис

- [ ] YooKassaService создан
- [ ] create_payment работает
- [ ] get_payment работает
- [ ] verify_webhook_signature работает
- [ ] Обработка ошибок работает

### Публичные API

- [ ] Валидация токена бота работает
- [ ] Создание платежа работает
- [ ] Регистрация компании работает
- [ ] Webhook от Юкассы работает
- [ ] Страница успешной оплаты создана

### Интеграция

- [ ] Подписка создается после оплаты
- [ ] Компания активируется
- [ ] Схема создается в фоне
- [ ] Миграции применяются

### Тестирование

- [ ] Тесты Юкассы пройдены
- [ ] Валидация токена протестирована
- [ ] Регистрация протестирована
- [ ] Webhook протестирован
- [ ] Нет ошибок в логах

### Окружение

- [ ] .env.example обновлен
- [ ] bot/config.py обновлен
- [ ] web/backend/app/config.py обновлен
- [ ] Переменные окружения задокументированы

---

## ⚠️ Риски и их решение

### Риск 1: Ошибки интеграции с Юкассой

**Вероятность:** Средняя  
**Влияние:** Высокое

**Меры предупреждения:**
- Использование тестового магазина
- Тестирование всех сценариев
- Обработка всех ошибок

**Решение при возникновении:**
- Проверка документации Юкассы
- Связь с поддержкой Юкассы
- Резервный способ оплаты

---

### Риск 2: Подделка webhook

**Вероятность:** Низкая  
**Влияние:** Высокое

**Меры предупреждения:**
- Проверка подписи webhook
- Проверка IP источника
- Двойная проверка данных

**Решение при возникновении:**
- Логирование всех webhook
- Ручная проверка платежей
- Блокировка подозрительных запросов

---

### Риск 3: Долгое время создания схемы

**Вероятность:** Средняя  
**Влияние:** Среднее

**Меры предупреждения:**
- Фоновое выполнение
- Уведомление о начале процесса
- Мониторинг выполнения

**Решение при возникновении:**
- Проверка логов
- Ручное выполнение миграций
- Повторный запуск

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить логи:
   ```bash
   docker compose logs web -f | grep yookassa
   ```

2. Проверить переменные окружения:
   ```bash
   docker compose exec web printenv | grep YOOKASSA
   ```

3. Проверить webhook:
   ```bash
   # Логи webhook
   docker compose logs web -f | grep webhook
   ```

4. Ручная проверка платежа:
   ```bash
   # Используем скрипт
   docker compose exec web python scripts/test_yookassa.py
   ```

---

**Этап 4 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

