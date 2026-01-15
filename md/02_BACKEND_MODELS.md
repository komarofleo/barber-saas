# Этап 2: Backend - Модели и Схемы

**Продолжительность:** 2-3 дня  
**Статус:** ✅ Завершен (см. `STAGE_2_COMPLETE.md`)  
**Дата завершения:** 2026-01-06  
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

Создать SQLAlchemy модели и Pydantic схемы для управления компаниями, подписками и платежами.

### Ожидаемый результат

- Все новые модели созданы и работают
- Все Pydantic схемы созданы и валидны
- CRUD функции для работы с моделями
- Инициализация тарифных планов
- Создание супер-админа

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Миграции из этапа 1 применены
- [ ] База данных готова для работы
- [ ] SQLAlchemy 2.0 настроен
- [ ] Pydantic установлен

### Технические требования

- Python 3.11+ установлен
- Все зависимости установлены
- Доступ к базе данных
- Понимание SQLAlchemy ORM

---

## 📝 Подзадачи

### Подзадача 2.1: Создать модель Company

**Описание:** Создать SQLAlchemy модель для таблицы companies.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/models/company.py
   ```

2. Определить модель:
   ```python
   from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, BigInteger, Text, Index
   from sqlalchemy.dialects.postgresql import JSONB
   from sqlalchemy.ext.declarative import declarative_base
   from datetime import datetime
   from sqlalchemy.orm import relationship

   Base = declarative_base()

   class Company(Base):
       """Салоны красоты (компании)"""
       __tablename__ = "companies"
       
       id = Column(Integer, primary_key=True, index=True)
       name = Column(String(255), nullable=False)
       code = Column(String(50), unique=True, nullable=False, index=True)
       email = Column(String(255), nullable=True)
       phone = Column(String(20), nullable=True)
       telegram_bot_token = Column(String(500), unique=True, nullable=True, index=True)
       telegram_bot_username = Column(String(255), nullable=True)
       webhook_url = Column(String(500), nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       is_active = Column(Boolean, default=True, nullable=False)
       subscription_status = Column(String(50), default='trial', nullable=False, index=True)
       subscription_end_date = Column(Date, nullable=True)
       max_users = Column(Integer, nullable=True)
       max_masters = Column(Integer, nullable=True)
       max_posts = Column(Integer, nullable=True)
       can_create_bookings = Column(Boolean, default=True, nullable=False)
       features = Column(JSONB, default={}, nullable=False)
       
       # Relationships
       subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")
       payments = relationship("Payment", back_populates="company", cascade="all, delete-orphan")
       users = relationship("User", back_populates="company")
   ```

3. Добавить индексы:
   - `idx_companies_code`
   - `idx_companies_subscription_status`
   - `idx_companies_is_active`

**Критерии выполнения:**
- [ ] Модель создана
- [ ] Все поля определены
- [ ] Индексы созданы
- [ ] Relationships определены
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.2: Создать модель Plan

**Описание:** Создать SQLAlchemy модель для тарифных планов.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/models/plan.py
   ```

2. Определить модель:
   ```python
   from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Index
   from sqlalchemy.dialects.postgresql import JSONB
   from datetime import datetime
   from sqlalchemy.orm import relationship

   class Plan(Base):
       """Тарифные планы"""
       __tablename__ = "plans"
       
       id = Column(Integer, primary_key=True, index=True)
       name = Column(String(50), unique=True, nullable=False)
       price_monthly = Column(Numeric(10, 2), nullable=False)
       max_users = Column(Integer, nullable=False)
       max_masters = Column(Integer, nullable=False)
       max_posts = Column(Integer, nullable=False)
       max_bookings_per_day = Column(Integer, nullable=False)
       features = Column(JSONB, default={}, nullable=False)
       is_active = Column(Boolean, default=True, nullable=False, index=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       subscriptions = relationship("Subscription", back_populates="plan")
   ```

3. Добавить индексы:
   - `idx_plans_active`

**Критерии выполнения:**
- [ ] Модель создана
- [ ] Все поля определены
- [ ] Индексы созданы
- [ ] Relationships определены
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.3: Создать модель Subscription

**Описание:** Создать SQLAlchemy модель для подписок.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/models/subscription.py
   ```

2. Определить модель:
   ```python
   from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Index
   from datetime import datetime, date
   from sqlalchemy.orm import relationship

   class Subscription(Base):
       """Подписки"""
       __tablename__ = "subscriptions"
       
       id = Column(Integer, primary_key=True, index=True)
       company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
       plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
       start_date = Column(Date, nullable=False)
       end_date = Column(Date, nullable=False)
       status = Column(String(50), default='active', nullable=False, index=True)
       auto_renewal = Column(Boolean, default=False, nullable=False)
       payment_method = Column(String(50), nullable=True)
       yookassa_payment_id = Column(String(255), nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       company = relationship("Company", back_populates="subscriptions")
       plan = relationship("Plan", back_populates="subscriptions")
       payments = relationship("Payment", back_populates="subscription")
   ```

3. Добавить индексы:
   - `idx_subscriptions_company`
   - `idx_subscriptions_status`
   - `idx_subscriptions_end_date`

**Критерии выполнения:**
- [ ] Модель создана
- [ ] Все поля определены
- [ ] Индексы созданы
- [ ] Foreign keys определены
- [ ] Relationships определены
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.4: Создать модель Payment

**Описание:** Создать SQLAlchemy модель для платежей.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/models/payment.py
   ```

2. Определить модель:
   ```python
   from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
   from sqlalchemy.dialects.postgresql import JSONB
   from datetime import datetime
   from sqlalchemy.orm import relationship

   class Payment(Base):
       """Платежи"""
       __tablename__ = "payments"
       
       id = Column(Integer, primary_key=True, index=True)
       company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
       subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
       amount = Column(Numeric(10, 2), nullable=False)
       currency = Column(String(3), default='RUB', nullable=False)
       payment_date = Column(DateTime, nullable=True, index=True)
       payment_method = Column(String(50), nullable=True)
       yookassa_payment_id = Column(String(255), unique=True, nullable=True, index=True)
       yookassa_payment_status = Column(String(50), nullable=True)
       status = Column(String(50), default='pending', nullable=False, index=True)
       receipt_url = Column(String(500), nullable=True)
       metadata = Column(JSONB, default={}, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
       
       # Relationships
       company = relationship("Company", back_populates="payments")
       subscription = relationship("Subscription", back_populates="payments")
   ```

3. Добавить индексы:
   - `idx_payments_company`
   - `idx_payments_status`
   - `idx_payments_payment_date`

**Критерии выполнения:**
- [ ] Модель создана
- [ ] Все поля определены
- [ ] Индексы созданы
- [ ] Foreign keys определены
- [ ] Relationships определены
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.5: Создать модель SuperAdmin

**Описание:** Создать SQLAlchemy модель для супер-админов.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/models/super_admin.py
   ```

2. Определить модель:
   ```python
   from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Index
   from datetime import datetime

   class SuperAdmin(Base):
       """Супер-админы"""
       __tablename__ = "super_admins"
       
       id = Column(Integer, primary_key=True, index=True)
       telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
       email = Column(String(255), unique=True, nullable=True)
       name = Column(String(255), nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
   ```

3. Добавить индексы:
   - `idx_super_admins_telegram`

**Критерии выполнения:**
- [ ] Модель создана
- [ ] Все поля определены
- [ ] Индексы созданы
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.6: Обновить модель User для связи с Company

**Описание:** Добавить поле company_id в модель User.

**Что нужно сделать:**

1. Открыть файл:
   ```
   shared/database/models.py
   ```

2. Обновить модель User:
   ```python
   class User(Base):
       """Пользователи системы"""
       __tablename__ = "users"
       
       id = Column(Integer, primary_key=True, index=True)
       telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
       username = Column(String(255), nullable=True)
       first_name = Column(String(255), nullable=True)
       last_name = Column(String(255), nullable=True)
       phone = Column(String(20), nullable=True, index=True)
       
       # Добавить поле для связи с компанией (если нужно)
       # company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
       
       is_admin = Column(Boolean, default=False, nullable=False)
       is_master = Column(Boolean, default=False, nullable=False)
       is_blocked = Column(Boolean, default=False, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       client = relationship("Client", back_populates="user", uselist=False, cascade="all, delete-orphan")
       master = relationship("Master", back_populates="user", uselist=False, cascade="all, delete-orphan")
       bookings_created = relationship("Booking", foreign_keys="Booking.created_by", back_populates="creator")
       booking_history = relationship("BookingHistory", back_populates="changed_by_user")
       notifications = relationship("Notification", back_populates="user")
       broadcasts_created = relationship("Broadcast", back_populates="creator")
       blocked_slots_created = relationship("BlockedSlot", back_populates="creator")
       
       # Добавить связь с компанией (если нужно)
       # company = relationship("Company", back_populates="users")
   ```

**Критерии выполнения:**
- [ ] Модель обновлена
- [ ] Поле добавлено (если нужно)
- [ ] Relationships обновлены
- [ ] Модель импортируется без ошибок

---

### Подзадача 2.7: Создать Pydantic схемы для Company

**Описание:** Создать Pydantic схемы для валидации данных компаний.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/schemas/company.py
   ```

2. Определить схемы:
   ```python
   from pydantic import BaseModel, EmailStr, Field, validator
   from typing import Optional, Dict, Any
   from datetime import date, datetime
   
   class CompanyBase(BaseModel):
       """Базовая схема компании"""
       name: str = Field(..., min_length=3, max_length=255, description="Название салона красоты")
       email: Optional[EmailStr] = Field(None, description="Email")
       phone: Optional[str] = Field(None, max_length=20, description="Телефон")
       telegram_bot_token: Optional[str] = Field(None, max_length=500, description="Токен бота")
       telegram_bot_username: Optional[str] = Field(None, max_length=255, description="Имя бота")
   
   class CompanyCreate(CompanyBase):
       """Схема создания компании"""
       code: str = Field(..., min_length=3, max_length=50, description="Уникальный код компании")
   
   class CompanyUpdate(BaseModel):
       """Схема обновления компании"""
       name: Optional[str] = Field(None, min_length=3, max_length=255)
       email: Optional[EmailStr] = None
       phone: Optional[str] = Field(None, max_length=20)
       telegram_bot_token: Optional[str] = Field(None, max_length=500)
       telegram_bot_username: Optional[str] = Field(None, max_length=255)
       webhook_url: Optional[str] = Field(None, max_length=500)
       is_active: Optional[bool] = None
       subscription_status: Optional[str] = Field(None, max_length=50)
       subscription_end_date: Optional[date] = None
       max_users: Optional[int] = Field(None, ge=1)
       max_masters: Optional[int] = Field(None, ge=1)
       max_posts: Optional[int] = Field(None, ge=1)
       can_create_bookings: Optional[bool] = None
       features: Optional[Dict[str, Any]] = None
   
   class CompanyResponse(CompanyBase):
       """Схема ответа компании"""
       id: int
       code: str
       created_at: datetime
       updated_at: datetime
       is_active: bool
       subscription_status: str
       subscription_end_date: Optional[date]
       max_users: Optional[int]
       max_masters: Optional[int]
       max_posts: Optional[int]
       can_create_bookings: bool
       features: Optional[Dict[str, Any]]
       
       class Config:
           from_attributes = True
   ```

**Критерии выполнения:**
- [ ] Все схемы созданы
- [ ] Валидаторы работают
- [ ] Описания полей добавлены
- [ ] Схемы тестируются

---

### Подзадача 2.8: Создать Pydantic схемы для Plan

**Описание:** Создать Pydantic схемы для тарифных планов.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/schemas/plan.py
   ```

2. Определить схемы:
   ```python
   from pydantic import BaseModel, Field
   from typing import Optional, Dict, Any
   from datetime import datetime
   from decimal import Decimal
   
   class PlanBase(BaseModel):
       """Базовая схема тарифного плана"""
       name: str = Field(..., min_length=3, max_length=50)
       price_monthly: Decimal = Field(..., gt=0, description="Цена в месяц")
       max_users: int = Field(..., ge=1, description="Максимальное количество пользователей")
       max_masters: int = Field(..., ge=1, description="Максимальное количество мастеров")
       max_posts: int = Field(..., ge=1, description="Максимальное количество постов")
       max_bookings_per_day: int = Field(..., ge=1, description="Максимальное количество записей в день")
       features: Optional[Dict[str, Any]] = Field(default={}, description="Фичи тарифа")
   
   class PlanCreate(PlanBase):
       """Схема создания тарифного плана"""
       pass
   
   class PlanUpdate(BaseModel):
       """Схема обновления тарифного плана"""
       name: Optional[str] = Field(None, min_length=3, max_length=50)
       price_monthly: Optional[Decimal] = Field(None, gt=0)
       max_users: Optional[int] = Field(None, ge=1)
       max_masters: Optional[int] = Field(None, ge=1)
       max_posts: Optional[int] = Field(None, ge=1)
       max_bookings_per_day: Optional[int] = Field(None, ge=1)
       features: Optional[Dict[str, Any]] = None
       is_active: Optional[bool] = None
   
   class PlanResponse(PlanBase):
       """Схема ответа тарифного плана"""
       id: int
       is_active: bool
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

**Критерии выполнения:**
- [ ] Все схемы созданы
- [ ] Валидаторы работают
- [ ] Decimal типы корректны
- [ ] Схемы тестируются

---

### Подзадача 2.9: Создать Pydantic схемы для Subscription

**Описание:** Создать Pydantic схемы для подписок.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/schemas/subscription.py
   ```

2. Определить схемы:
   ```python
   from pydantic import BaseModel, Field
   from typing import Optional
   from datetime import date, datetime
   
   class SubscriptionBase(BaseModel):
       """Базовая схема подписки"""
       company_id: int = Field(..., ge=1)
       plan_id: int = Field(..., ge=1)
       start_date: date = Field(..., description="Дата начала подписки")
       end_date: date = Field(..., description="Дата окончания подписки")
       auto_renewal: bool = Field(default=False, description="Автоматическое продление")
       payment_method: Optional[str] = Field(None, max_length=50, description="Метод оплаты")
   
   class SubscriptionCreate(SubscriptionBase):
       """Схема создания подписки"""
       pass
   
   class SubscriptionUpdate(BaseModel):
       """Схема обновления подписки"""
       status: Optional[str] = Field(None, max_length=50)
       auto_renewal: Optional[bool] = None
       payment_method: Optional[str] = Field(None, max_length=50)
   
   class SubscriptionResponse(SubscriptionBase):
       """Схема ответа подписки"""
       id: int
       status: str
       yookassa_payment_id: Optional[str]
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

**Критерии выполнения:**
- [ ] Все схемы созданы
- [ ] Валидаторы работают
- [ ] Даты корректны
- [ ] Схемы тестируются

---

### Подзадача 2.10: Создать Pydantic схемы для Payment

**Описание:** Создать Pydantic схемы для платежей.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/schemas/payment.py
   ```

2. Определить схемы:
   ```python
   from pydantic import BaseModel, Field
   from typing import Optional, Dict, Any
   from datetime import datetime
   from decimal import Decimal
   
   class PaymentBase(BaseModel):
       """Базовая схема платежа"""
       company_id: int = Field(..., ge=1)
       subscription_id: Optional[int] = Field(None, ge=1)
       amount: Decimal = Field(..., gt=0, description="Сумма платежа")
       currency: str = Field(default="RUB", max_length=3)
       payment_method: Optional[str] = Field(None, max_length=50)
   
   class PaymentCreate(PaymentBase):
       """Схема создания платежа"""
       pass
   
   class PaymentUpdate(BaseModel):
       """Схема обновления платежа"""
       status: Optional[str] = Field(None, max_length=50)
       yookassa_payment_status: Optional[str] = Field(None, max_length=50)
       payment_date: Optional[datetime] = None
       receipt_url: Optional[str] = Field(None, max_length=500)
   
   class PaymentResponse(PaymentBase):
       """Схема ответа платежа"""
       id: int
       yookassa_payment_id: Optional[str]
       yookassa_payment_status: Optional[str]
       status: str
       payment_date: Optional[datetime]
       receipt_url: Optional[str]
       metadata: Optional[Dict[str, Any]]
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

**Критерии выполнения:**
- [ ] Все схемы созданы
- [ ] Валидаторы работают
- [ ] Decimal типы корректны
- [ ] Схемы тестируются

---

### Подзадача 2.11: Создать Pydantic схемы для SuperAdmin

**Описание:** Создать Pydantic схемы для супер-админов.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/schemas/super_admin.py
   ```

2. Определить схемы:
   ```python
   from pydantic import BaseModel, EmailStr, Field
   from typing import Optional
   from datetime import datetime
   
   class SuperAdminBase(BaseModel):
       """Базовая схема супер-админа"""
       telegram_id: int = Field(..., gt=0, description="Telegram ID")
       email: Optional[EmailStr] = Field(None, description="Email")
       name: Optional[str] = Field(None, max_length=255, description="Имя")
   
   class SuperAdminCreate(SuperAdminBase):
       """Схема создания супер-админа"""
       pass
   
   class SuperAdminUpdate(BaseModel):
       """Схема обновления супер-админа"""
       email: Optional[EmailStr] = None
       name: Optional[str] = Field(None, max_length=255)
   
   class SuperAdminResponse(SuperAdminBase):
       """Схема ответа супер-админа"""
       id: int
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

**Критерии выполнения:**
- [ ] Все схемы созданы
- [ ] Валидаторы работают
- [ ] Telegram ID корректен
- [ ] Схемы тестируются

---

### Подзадача 2.12: Создать CRUD функции для Company

**Описание:** Создать CRUD функции для работы с компаниями.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/services/company_service.py
   ```

2. Определить функции:
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, and_
   from typing import Optional, List
   from datetime import date, datetime
   
   from app.models.company import Company
   
   async def get_company_by_id(session: AsyncSession, company_id: int) -> Optional[Company]:
       """Получить компанию по ID"""
       result = await session.execute(
           select(Company).where(Company.id == company_id)
       )
       return result.scalar_one_or_none()
   
   async def get_company_by_code(session: AsyncSession, code: str) -> Optional[Company]:
       """Получить компанию по коду"""
       result = await session.execute(
           select(Company).where(Company.code == code)
       )
       return result.scalar_one_or_none()
   
   async def get_companies(
       session: AsyncSession,
       skip: int = 0,
       limit: int = 100,
       is_active: Optional[bool] = None,
       subscription_status: Optional[str] = None
   ) -> List[Company]:
       """Получить список компаний с фильтрами"""
       query = select(Company)
       
       conditions = []
       if is_active is not None:
           conditions.append(Company.is_active == is_active)
       if subscription_status is not None:
           conditions.append(Company.subscription_status == subscription_status)
       
       if conditions:
           query = query.where(and_(*conditions))
       
       query = query.offset(skip).limit(limit).order_by(Company.created_at.desc())
       result = await session.execute(query)
       return list(result.scalars().all())
   
   async def count_companies(
       session: AsyncSession,
       is_active: Optional[bool] = None,
       subscription_status: Optional[str] = None
   ) -> int:
       """Посчитать количество компаний"""
       from sqlalchemy import func
       
       query = select(func.count(Company.id))
       
       conditions = []
       if is_active is not None:
           conditions.append(Company.is_active == is_active)
       if subscription_status is not None:
           conditions.append(Company.subscription_status == subscription_status)
       
       if conditions:
           query = query.where(and_(*conditions))
       
       result = await session.execute(query)
       return result.scalar() or 0
   
   async def create_company(session: AsyncSession, company_data: dict) -> Company:
       """Создать компанию"""
       company = Company(**company_data)
       session.add(company)
       await session.commit()
       await session.refresh(company)
       return company
   
   async def update_company(
       session: AsyncSession,
       company_id: int,
       company_data: dict
   ) -> Optional[Company]:
       """Обновить компанию"""
       company = await get_company_by_id(session, company_id)
       if not company:
           return None
       
       for field, value in company_data.items():
           if hasattr(company, field):
               setattr(company, field, value)
       
       company.updated_at = datetime.utcnow()
       await session.commit()
       await session.refresh(company)
       return company
   
   async def delete_company(session: AsyncSession, company_id: int) -> bool:
       """Удалить компанию"""
       company = await get_company_by_id(session, company_id)
       if not company:
           return False
       
       await session.delete(company)
       await session.commit()
       return True
   ```

**Критерии выполнения:**
- [ ] Все функции созданы
- [ ] Асинхронность работает
- [ ] Фильтры работают
- [ ] Пагинация работает
- [ ] Функции тестируются

---

### Подзадача 2.13: Создать CRUD функции для Subscription

**Описание:** Создать CRUD функции для работы с подписками.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/services/subscription_service.py
   ```

2. Определить функции (аналогично company_service.py):
   - `get_subscription_by_id`
   - `get_subscriptions_by_company`
   - `create_subscription`
   - `update_subscription`
   - `delete_subscription`
   - `get_active_subscription`
   - `get_expiring_subscriptions`

**Критерии выполнения:**
- [ ] Все функции созданы
- [ ] Асинхронность работает
- [ ] Функции тестируются

---

### Подзадача 2.14: Создать CRUD функции для Payment

**Описание:** Создать CRUD функции для работы с платежами.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/services/payment_service.py
   ```

2. Определить функции:
   - `get_payment_by_id`
   - `get_payments_by_company`
   - `create_payment`
   - `update_payment`
   - `get_payments_with_stats`

**Критерии выполнения:**
- [ ] Все функции созданы
- [ ] Асинхронность работает
- [ ] Статистика считается
- [ ] Функции тестируются

---

### Подзадача 2.15: Инициализировать тарифные планы

**Описание:** Создать скрипт для инициализации тарифных планов.

**Что нужно сделать:**

1. Создать файл:
   ```
   scripts/init_plans.py
   ```

2. Определить логику:
   ```python
   import asyncio
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.database import get_db
   from app.models.plan import Plan
   
   async def init_plans():
       """Инициализация тарифных планов"""
       async for session in get_db():
           plans_data = [
               {
                   "name": "Starter",
                   "price_monthly": 2990.00,
                   "max_users": 100,
                   "max_masters": 3,
                   "max_posts": 2,
                   "max_bookings_per_day": 20,
                   "features": {
                       "notifications": True,
                       "statistics": False,
                       "export": False,
                       "promocodes": False
                   }
               },
               {
                   "name": "Pro",
                   "price_monthly": 4990.00,
                   "max_users": 500,
                   "max_masters": 10,
                   "max_posts": 5,
                   "max_bookings_per_day": 50,
                   "features": {
                       "notifications": True,
                       "statistics": True,
                       "export": True,
                       "promocodes": True,
                       "broadcasts": False
                   }
               },
               {
                   "name": "Business",
                   "price_monthly": 9990.00,
                   "max_users": 9999,
                   "max_masters": 9999,
                   "max_posts": 9999,
                   "max_bookings_per_day": 9999,
                   "features": {
                       "notifications": True,
                       "statistics": True,
                       "export": True,
                       "promocodes": True,
                       "broadcasts": True,
                       "api_access": True
                   }
               }
           ]
           
           for plan_data in plans_data:
               # Проверяем, существует ли план
               existing_plan = await session.execute(
                   select(Plan).where(Plan.name == plan_data["name"])
               ).scalar_one_or_none()
               
               if not existing_plan:
                   plan = Plan(**plan_data, is_active=True)
                   session.add(plan)
                   print(f"Создан план: {plan_data['name']}")
               else:
                   print(f"План уже существует: {plan_data['name']}")
           
           await session.commit()
           print("✅ Инициализация планов завершена!")
   
   if __name__ == "__main__":
       asyncio.run(init_plans())
   ```

3. Запустить скрипт:
   ```bash
   docker compose exec web python scripts/init_plans.py
   ```

**Критерии выполнения:**
- [ ] Скрипт создан
- [ ] Три плана созданы
- [ ] Проверка на дубликаты работает
- [ ] Скрипт выполняется успешно

---

### Подзадача 2.16: Создать супер-админа

**Описание:** Создать скрипт для создания первого супер-админа.

**Что нужно сделать:**

1. Создать файл:
   ```
   scripts/init_super_admin.py
   ```

2. Определить логику:
   ```python
   import asyncio
   import sys
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.database import get_db
   from app.models.super_admin import SuperAdmin
   
   async def create_super_admin(telegram_id: int, email: str = None, name: str = None):
       """Создание супер-админа"""
       async for session in get_db():
           # Проверяем, существует ли уже
           existing = await session.execute(
               select(SuperAdmin).where(SuperAdmin.telegram_id == telegram_id)
           ).scalar_one_or_none()
           
           if existing:
               print(f"⚠️ Супер-админ с Telegram ID {telegram_id} уже существует")
               return existing
           
           # Создаем
           super_admin = SuperAdmin(
               telegram_id=telegram_id,
               email=email,
               name=name
           )
           session.add(super_admin)
           await session.commit()
           await session.refresh(super_admin)
           
           print(f"✅ Супер-админ создан:")
           print(f"   Telegram ID: {super_admin.telegram_id}")
           print(f"   Email: {super_admin.email}")
           print(f"   Имя: {super_admin.name}")
           
           return super_admin
   
   if __name__ == "__main__":
       if len(sys.argv) < 2:
           print("Использование: python init_super_admin.py <telegram_id> [email] [name]")
           sys.exit(1)
       
       telegram_id = int(sys.argv[1])
       email = sys.argv[2] if len(sys.argv) > 2 else None
       name = sys.argv[3] if len(sys.argv) > 3 else None
       
       asyncio.run(create_super_admin(telegram_id, email, name))
   ```

3. Запустить скрипт:
   ```bash
   docker compose exec web python scripts/init_super_admin.py 329621295 admin@example.com "Super Admin"
   ```

**Критерии выполнения:**
- [ ] Скрипт создан
- [ ] Супер-админ создан
- [ ] Проверка на дубликаты работает
- [ ] Скрипт выполняется успешно

---

## ✅ Чек-лист этапа

### SQLAlchemy модели

- [ ] Модель Company создана
- [ ] Модель Plan создана
- [ ] Модель Subscription создана
- [ ] Модель Payment создана
- [ ] Модель SuperAdmin создана
- [ ] Модель User обновлена
- [ ] Все relationships определены
- [ ] Все индексы созданы

### Pydantic схемы

- [ ] Схемы для Company созданы
- [ ] Схемы для Plan созданы
- [ ] Схемы для Subscription созданы
- [ ] Схемы для Payment созданы
- [ ] Схемы для SuperAdmin созданы
- [ ] Все валидаторы работают
- [ ] Все схемы протестированы

### CRUD функции

- [ ] CRUD для Company создан
- [ ] CRUD для Subscription создан
- [ ] CRUD для Payment создан
- [ ] Все функции асинхронные
- [ ] Все функции протестированы

### Инициализация

- [ ] Скрипт init_plans.py создан
- [ ] Тарифные планы инициализированы
- [ ] Скрипт init_super_admin.py создан
- [ ] Супер-админ создан

### Тестирование

- [ ] Модели работают с БД
- [ ] Схемы валидируют данные
- [ ] CRUD функции работают
- [ ] Нет ошибок в логах

---

## ⚠️ Риски и их решение

### Риск 1: Ошибки в связях моделей

**Вероятность:** Средняя  
**Влияние:** Среднее

**Меры предупреждения:**
- Проверка foreign keys
- Тестирование relationships
- Проверка каскадного удаления

**Решение при возникновении:**
- Исправление foreign keys
- Изменение каскадного удаления
- Пересоздание связей

---

### Риск 2: Несовместимость типов данных

**Вероятность:** Низкая  
**Влияние:** Низкое

**Меры предупреждения:**
- Проверка типов в Pydantic
- Проверка типов в SQLAlchemy
- Конвертация типов

**Решение при возникновении:**
- Использование кастомных валидаторов
- Преобразование типов
- Использование Any для JSONB

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить модели:
   ```bash
   docker compose exec web python -c "from app.models.company import Company; print(Company)"
   ```

2. Проверить схемы:
   ```bash
   docker compose exec web python -c "from app.schemas.company import CompanyResponse; print(CompanyResponse)"
   ```

3. Проверить БД:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "\dt public"
   ```

---

**Этап 2 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

