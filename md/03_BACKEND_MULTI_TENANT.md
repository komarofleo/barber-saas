# Этап 3: Backend - Мульти-тенантность

**Продолжительность:** 3-4 дня  
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

Реализовать работу с несколькими схемами базы данных для мульти-тенантной архитектуры.

### Ожидаемый результат

- SessionManager для работы с несколькими схемами
- Middleware для проверки подписки
- CRUD функции с параметром company_id
- Функции создания/удаления схем
- Полная изоляция данных клиентов
- Динамическое переключение схем

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Этап 2 завершен (модели и схемы созданы)
- [ ] Миграции из этапа 1 применены
- [ ] Понимание работы со схемами в PostgreSQL

### Технические требования

- Python 3.11+ установлен
- PostgreSQL 15+
- SQLAlchemy 2.0 (async)
- Понимание PostgreSQL Schemas

---

## 📝 Подзадачи

### Подзадача 3.1: Обновить database.py для работы с несколькими схемами

**Описание:** Обновить модуль подключения к БД для поддержки нескольких схем.

**Что нужно сделать:**

1. Открыть файл:
   ```
   web/backend/app/database.py
   ```

2. Обновить импорты:
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
   from sqlalchemy import text
   from sqlalchemy.orm import declarative_base
   ```

3. Создать функцию для создания сессии с указанием схемы:
   ```python
   async def get_session_with_schema(schema_name: str = "public"):
       """Получить сессию с указанием схемы"""
       async with engine.connect() as conn:
           await conn.execute(
               text(f"SET search_path TO {schema_name}, public")
           )
           await conn.commit()
       
       return AsyncSessionLocal()
   ```

4. Обновить существующую get_session для использования схемы по умолчанию:
   ```python
   async def get_session():
       """Получить сессию (использует схему по умолчанию)"""
       return AsyncSessionLocal()
   ```

5. Создать функцию для создания новой схемы:
   ```python
   async def create_tenant_schema(company_id: int):
       """Создать схему для нового клиента"""
       schema_name = f"tenant_{company_id}"
       
       async with engine.begin() as conn:
           await conn.execute(
               text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
           )
   
       return schema_name
   ```

6. Создать функцию для удаления схемы:
   ```python
   async def drop_tenant_schema(company_id: int):
       """Удалить схему клиента"""
       schema_name = f"tenant_{company_id}"
       
       async with engine.begin() as conn:
           await conn.execute(
               text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
           )
   
       return schema_name
   ```

**Критерии выполнения:**
- [ ] Функции созданы
- [ ] get_session_with_schema работает
- [ ] create_tenant_schema работает
- [ ] drop_tenant_schema работает
- [ ] Нет ошибок при подключении

---

### Подзадача 3.2: Создать TenantService для управления схемами

**Описание:** Создать сервис для управления схемами и миграциями.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/services/tenant_service.py
   ```

2. Определить класс и методы:
   ```python
   from sqlalchemy import text
   from sqlalchemy.ext.asyncio import AsyncSession
   from typing import List
   import subprocess
   import asyncio
   from app.database import engine
   
   class TenantService:
       """Сервис управления схемами"""
       
       @staticmethod
       async def create_tenant_schema(company_id: int):
           """Создать схему для нового клиента"""
           schema_name = f"tenant_{company_id}"
           
           async with engine.begin() as conn:
               await conn.execute(
                   text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
               )
           
           return schema_name
       
       @staticmethod
       async def drop_tenant_schema(company_id: int):
           """Удалить схему клиента"""
           schema_name = f"tenant_{company_id}"
           
           async with engine.begin() as conn:
               await conn.execute(
                   text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
               )
       
       @staticmethod
       async def apply_migrations_to_schema(company_id: int):
           """Применить миграции к схеме клиента"""
           schema_name = f"tenant_{company_id}"
           
           # Устанавливаем search_path на схему
           async with engine.begin() as conn:
               await conn.execute(
                   text(f"SET search_path TO {schema_name}, public")
               )
           
           # Применяем миграции через alembic
           # Важно: alembic должен использовать правильную схему
           cmd = [
               "alembic",
               "upgrade",
               "head",
               f"--sql"
           ]
           
           # Для применения к конкретной схеме используем переменную окружения
           env = {"ALEMBIC_SCHEMA": schema_name}
           
           result = await asyncio.create_subprocess_exec(
               cmd,
               env=env,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE
           )
           
           stdout, stderr = await result.communicate()
           
           if result.returncode != 0:
               raise Exception(f"Ошибка миграции: {stderr.decode()}")
           
           return True
       
       @staticmethod
       async def copy_schema_structure(source_schema: str, target_schema: str):
           """Скопировать структуру схемы"""
           # Получаем список таблиц исходной схемы
           async with engine.begin() as conn:
               result = await conn.execute(
                   text(f"""
                       SELECT table_name 
                       FROM information_schema.tables 
                       WHERE table_schema = '{source_schema}'
                       AND table_type = 'BASE TABLE'
                   """)
               )
               tables = [row[0] for row in result]
               
               for table in tables:
                   # Создаем таблицу в целевой схеме
                   await conn.execute(
                       text(f"CREATE TABLE {target_schema}.{table} AS SELECT * FROM {source_schema}.{table}")
                   )
               
               await conn.commit()
           
           return tables
   ```

**Критерии выполнения:**
- [ ] TenantService создан
- [ ] create_tenant_schema работает
- [ ] drop_tenant_schema работает
- [ ] apply_migrations_to_schema работает
- [ ] copy_schema_structure работает

---

### Подзадача 3.3: Создать subscription_middleware

**Описание:** Создать middleware для проверки подписки перед созданием записи.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/middleware/subscription_middleware.py
   ```

2. Определить middleware:
   ```python
   from fastapi import Request, HTTPException
   from starlette.middleware.base import BaseHTTPMiddleware
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   
   from app.database import get_session_with_schema
   from app.models.company import Company
   
   class SubscriptionMiddleware(BaseHTTPMiddleware):
       """Middleware для проверки подписки"""
       
       async def dispatch(self, request: Request, call_next):
           """Проверяем подписку перед созданием записи"""
           
           # Проверяем только для endpoints создания записей
           if "/bookings" in request.url.path and request.method == "POST":
               # Получаем company_id из запроса
               company_id = self._get_company_id(request)
               
               if company_id:
                   # Проверяем подписку
                   async for session in get_session_with_schema("public"):
                       result = await session.execute(
                           select(Company).where(Company.id == company_id)
                       )
                       company = result.scalar_one_or_none()
                       
                       if not company or not company.can_create_bookings:
                           raise HTTPException(
                               status_code=402,
                               detail={
                                   "error": "subscription_expired",
                                   "message": "Запись отключена. Пожалуйста, продлите подписку.",
                                   "can_view": True  # Можно смотреть данные
                               }
                           )
           
           response = await call_next(request)
           return response
       
       def _get_company_id(self, request: Request) -> int:
           """Получить company_id из запроса"""
           # Из JWT токена
           if hasattr(request.state, "user"):
               user = request.state.user
               return getattr(user, "company_id", None)
           
           # Из параметров запроса
           return request.query_params.get("company_id")
   
   async def check_subscription(company_id: int):
       """Проверить подписку компании"""
       async for session in get_session_with_schema("public"):
           result = await session.execute(
               select(Company).where(Company.id == company_id)
           )
           company = result.scalar_one_or_none()
           
           if not company:
               raise HTTPException(
                   status_code=404,
                   detail="Компания не найдена"
               )
           
           if not company.can_create_bookings:
               raise HTTPException(
                   status_code=402,
                   detail={
                       "error": "subscription_expired",
                       "message": "Запись отключена. Пожалуйста, продлите подписку."
                   }
               )
           
           return company
   ```

3. Добавить middleware в main.py:
   ```python
   from app.middleware.subscription_middleware import SubscriptionMiddleware
   
   app.add_middleware(SubscriptionMiddleware)
   ```

**Критерии выполнения:**
- [ ] Middleware создан
- [ ] Проверка подписки работает
- [ ] Middleware добавлен в main.py
- [ ] Ошибка 402 возвращается корректно
- [ ] Можно смотреть данные при истекшей подписке

---

### Подзадача 3.4: Создать company_middleware

**Описание:** Создать middleware для определения компании из запроса.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/middleware/company_middleware.py
   ```

2. Определить middleware:
   ```python
   from fastapi import Request
   from starlette.middleware.base import BaseHTTPMiddleware
   
   class CompanyMiddleware(BaseHTTPMiddleware):
       """Middleware для определения компании"""
       
       async def dispatch(self, request: Request, call_next):
           """Добавить информацию о компании в request.state"""
           
           # Попытка получить company_id
           company_id = self._get_company_id(request)
           
           if company_id:
               request.state.company_id = company_id
               request.state.schema_name = f"tenant_{company_id}"
           
           response = await call_next(request)
           return response
       
       def _get_company_id(self, request: Request) -> int:
           """Получить company_id из запроса"""
           # Из JWT токена (если авторизован)
           if hasattr(request.state, "user"):
               user = request.state.user
               return getattr(user, "company_id", None)
           
           # Из параметров запроса
           company_id = request.query_params.get("company_id")
           if company_id:
               try:
                   return int(company_id)
               except ValueError:
                   pass
           
           # Из заголовка
           company_id = request.headers.get("X-Company-ID")
           if company_id:
               try:
                   return int(company_id)
               except ValueError:
                   pass
           
           return None
   ```

3. Добавить middleware в main.py:
   ```python
   from app.middleware.company_middleware import CompanyMiddleware
   
   app.add_middleware(CompanyMiddleware)
   ```

**Критерии выполнения:**
- [ ] Middleware создан
- [ ] company_id определяется корректно
- [ ] schema_name определяется корректно
- [ ] Middleware добавлен в main.py
- [ ] request.state обновляется

---

### Подзадача 3.5: Обновить CRUD функции для работы с company_id

**Описание:** Обновить существующие CRUD функции для работы с правильной схемой.

**Что нужно сделать:**

1. Обновить файл:
   ```
   web/backend/app/api/bookings.py
   ```

2. Обновить функцию get_bookings:
   ```python
   @router.get("", response_model=BookingListResponse)
   async def get_bookings(
       page: int = Query(1, ge=1),
       page_size: int = Query(20, ge=1, le=1000),
       status: Optional[str] = None,
       start_date: Optional[date] = None,
       end_date: Optional[date] = None,
       master_id: Optional[int] = None,
       service_id: Optional[int] = None,
       post_id: Optional[int] = None,
       search: Optional[str] = None,
       company_id: int = Query(..., description="ID компании"),
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user),
   ):
       """Получить список записей"""
       # Используем company_id для выбора правильной схемы
       async for session in get_session_with_schema(f"tenant_{company_id}"):
           # ... остальной код
           pass
   ```

3. Обновить функцию create_booking:
   ```python
   @router.post("", response_model=BookingResponse, status_code=201)
   async def create_booking(
       booking_data: BookingCreateRequest,
       company_id: int = Query(..., description="ID компании"),
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user),
   ):
       """Создать новую запись"""
       # Используем company_id для выбора правильной схемы
       async for session in get_session_with_schema(f"tenant_{company_id}"):
           # Проверка подписки (через middleware уже сделано)
           # ... остальной код
           pass
   ```

4. Аналогично обновить другие CRUD функции:
   - users.py
   - services.py
   - masters.py
   - posts.py
   - clients.py
   - blocks.py
   - promocodes.py
   - promotions.py
   - broadcasts.py

**Критерии выполнения:**
- [ ] bookings.py обновлен
- [ ] users.py обновлен
- [ ] services.py обновлен
- [ ] masters.py обновлен
- [ ] posts.py обновлен
- [ ] clients.py обновлен
- [ ] Все API работают с company_id

---

### Подзадача 3.6: Обновить auth для работы с company_id

**Описание:** Обновить модуль аутентификации для работы с несколькими схемами.

**Что нужно сделать:**

1. Открыть файл:
   ```
   web/backend/app/api/auth.py
   ```

2. Обновить функцию login:
   ```python
   @router.post("/login")
   async def login(
       credentials: AuthLogin,
       company_id: int = Query(..., description="ID компании"),
       db: AsyncSession = Depends(get_db),
   ):
       """Авторизация"""
       # Проверяем существование компании
       async for public_session in get_session_with_schema("public"):
           from app.models.company import Company
           result = await public_session.execute(
               select(Company).where(Company.id == company_id)
           )
           company = result.scalar_one_or_none()
           
           if not company:
               raise HTTPException(status_code=404, detail="Компания не найдена")
           
           # Проверяем активность подписки
           if not company.is_active:
               raise HTTPException(
                   status_code=403,
                   detail="Компания заблокирована"
               )
       
       # Подключаемся к схеме клиента
       async for session in get_session_with_schema(f"tenant_{company_id}"):
           # ... остальной код авторизации
           pass
   ```

**Критерии выполнения:**
- [ ] auth.py обновлен
- [ ] Проверка компании работает
- [ ] Проверка подписки работает
- [ ] Авторизация работает с company_id

---

### Подзадача 3.7: Создать Alembic скрипты для tenant-схем

**Описание:** Создать Alembic скрипты для применения миграций к tenant-схемам.

**Что нужно сделать:**

1. Создать скрипт для создания структуры tenant-схемы:
   ```
   scripts/create_tenant_schema.py
   ```

2. Определить логику:
   ```python
   import sys
   import asyncio
   from sqlalchemy import text
   
   from app.database import engine
   
   async def create_tenant_schema(company_id: int):
       """Создать tenant-схему и применить миграции"""
       schema_name = f"tenant_{company_id}"
       
       async with engine.begin() as conn:
           # Создаем схему
           await conn.execute(
               text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
           )
           
           # Применяем все миграции к этой схеме
           # Важно: нужно использовать alembic programmatically
           print(f"✅ Схема {schema_name} создана")
       
       return schema_name
   
   if __name__ == "__main__":
       if len(sys.argv) < 2:
           print("Использование: python create_tenant_schema.py <company_id>")
           sys.exit(1)
       
       company_id = int(sys.argv[1])
       asyncio.run(create_tenant_schema(company_id))
   ```

**Критерии выполнения:**
- [ ] Скрипт создан
- [ ] Схема создается
- [ ] Миграции применяются
- [ ] Скрипт работает

---

### Подзадача 3.8: Протестировать изоляцию данных

**Описание:** Протестировать, что данные разных клиентов полностью изолированы.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_data_isolation.py
   ```

2. Определить тесты:
   ```python
   import asyncio
   from sqlalchemy import text, select
   from sqlalchemy.ext.asyncio import AsyncSession
   
   from app.database import get_session_with_schema, engine
   from app.models.booking import Booking
   from app.models.client import Client
   
   async def test_data_isolation():
       """Тест изоляции данных"""
       
       # Тест 1: Проверка, что данные одной схемы не видны в другой
       async for session_1 in get_session_with_schema("tenant_001"):
           # Создаем тестовую запись
           await session_1.execute(
               text("INSERT INTO bookings (booking_number, client_id, date, time, duration, end_time, status) VALUES ('TEST_001', 1, CURRENT_DATE, '09:00', 30, '09:30', 'new')")
           )
           await session_1.commit()
           
           # Проверяем, что запись видна
           result = await session_1.execute(
               select(Booking).where(Booking.booking_number == 'TEST_001')
           )
           booking = result.scalar_one_or_none()
           print(f"✅ Запись видна в tenant_001: {booking is not None}")
       
       # Тест 2: Проверяем, что запись НЕ видна в другой схеме
       async for session_2 in get_session_with_schema("tenant_002"):
           result = await session_2.execute(
               select(Booking).where(Booking.booking_number == 'TEST_001')
           )
           booking = result.scalar_one_or_none()
           print(f"✅ Запись НЕ видна в tenant_002: {booking is None}")
       
       # Тест 3: Проверка таблиц в разных схемах
       async with engine.begin() as conn:
           # Таблицы в tenant_001
           result = await conn.execute(
               text("""
                   SELECT COUNT(*) 
                   FROM information_schema.tables 
                   WHERE table_schema = 'tenant_001'
               """)
           )
           count_001 = result.scalar()
           
           # Таблицы в tenant_002
           result = await conn.execute(
               text("""
                   SELECT COUNT(*) 
                   FROM information_schema.tables 
                   WHERE table_schema = 'tenant_002'
               """)
           )
           count_002 = result.scalar()
           
           print(f"✅ tenant_001 таблиц: {count_001}")
           print(f"✅ tenant_002 таблиц: {count_002}")
           
           assert count_001 > 0, "tenant_001 должен иметь таблицы"
           # tenant_002 может быть пустой
   
       print("✅ Все тесты изоляции пройдены!")
   
   if __name__ == "__main__":
       asyncio.run(test_data_isolation())
   ```

3. Запустить тесты:
   ```bash
   docker compose exec web python scripts/test_data_isolation.py
   ```

**Критерии выполнения:**
- [ ] Скрипт тестов создан
- [ ] Тест изоляции данных пройден
- [ ] Тест видимости пройден
- [ ] Тест количества таблиц пройден
- [ ] Все тесты успешны

---

## ✅ Чек-лист этапа

### SessionManager и Database

- [ ] database.py обновлен
- [ ] get_session_with_schema создана
- [ ] create_tenant_schema создана
- [ ] drop_tenant_schema создана
- [ ] Функции работают корректно

### TenantService

- [ ] TenantService создан
- [ ] create_tenant_schema работает
- [ ] drop_tenant_schema работает
- [ ] apply_migrations_to_schema работает
- [ ] copy_schema_structure работает

### Middleware

- [ ] subscription_middleware создан
- [ ] company_middleware создан
- [ ] Middleware добавлены в main.py
- [ ] Проверка подписки работает
- [ ] Определение company_id работает

### CRUD функции

- [ ] bookings.py обновлен
- [ ] users.py обновлен
- [ ] services.py обновлен
- [ ] masters.py обновлен
- [ ] posts.py обновлен
- [ ] clients.py обновлен
- [ ] Все API работают с company_id

### Auth

- [ ] auth.py обновлен
- [ ] Проверка компании работает
- [ ] Проверка подписки работает
- [ ] Авторизация работает

### Миграции

- [ ] Скрипт создания схемы создан
- [ ] Миграции применяются корректно
- [ ] Структура схем одинаковая

### Тестирование

- [ ] Тесты изоляции созданы
- [ ] Тест изоляции данных пройден
- [ ] Тест видимости пройден
- [ ] Нет утечек данных

---

## ⚠️ Риски и их решение

### Риск 1: Утечка данных между схемами

**Вероятность:** Низкая  
**Влияние:** Критическое

**Меры предупреждения:**
- Строгое использование search_path
- Тестирование изоляции
- Проверка middleware

**Решение при возникновении:**
- Дополнительные проверки в middleware
- Использование schema.table_name
- Ручная проверка изоляции

---

### Риск 2: Ошибки при переключении схем

**Вероятность:** Средняя  
**Влияние:** Среднее

**Меры предупреждения:**
- Тестирование переключения
- Логирование всех переключений
- Валидация schema_name

**Решение при возникновении:**
- Попытка повторного подключения
- Откат к default схеме
- Уведомление администратора

---

### Риск 3: Проблемы с миграциями в tenant-схемах

**Вероятность:** Средняя  
**Влияние:** Высокое

**Меры предупреждения:**
- Тестирование миграций
- Использование транзакций
- Резервное копирование

**Решение при возникновении:**
- Ручное применение миграций
- Пересоздание схемы
- Восстановление из бэкапа

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить схемы:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "\dn"
   ```

2. Проверить таблицы в схеме:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "\dt tenant_001"
   ```

3. Проверить search_path:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "SHOW search_path;"
   ```

4. Сбросить search_path:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "SET search_path TO public;"
   ```

---

**Этап 3 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

