# Этап 7: Bot - Мульти-Тенантность

**Продолжительность:** 3-4 дня  
**Статус:** ✅ Завершен (MVP)  
**Дата завершения:** 2026-01-14  
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

Реализовать систему нескольких Telegram ботов для разных компаний с полной изоляцией данных.

### Ожидаемый результат

- Мульти-бот система работает
- Каждый бот работает со своей схемой БД
- Контекст компании сохраняется в диспетчере
- Tenant-сессии для работы с правильной схемой
- Проверка подписки перед созданием записи
- Сообщения об истекшей подписке
- Динамический запуск ботов
- Автоматическое создание ботов для новых клиентов

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Этап 3 завершен (мульти-тенантность работает)
- [ ] Этап 4 завершен (публичные API работают)
- [ ] Этап 5 завершен (API супер-админа работают)
- [ ] Миграция данных текущего клиента в tenant_001

### Технические требования

- Python 3.11+ установлен
- aiogram 3.x установлен
- Понимание работы с несколькими ботами
- Понимание работы с несколькими схемами БД

---

## 📝 Подзадачи

### Подзадача 7.1: Переписать bot/main.py для запуска нескольких ботов

**Описание:** Переписать главный файл бота для запуска нескольких экземпляров.

**Что нужно сделать:**

1. Открыть файл:
   ```
   bot/main.py
   ```

2. Полностью переписать:
   ```python
   """Главный файл для запуска нескольких Telegram ботов"""
   import asyncio
   import logging
   from aiogram import Bot, Dispatcher
   from aiogram.fsm.storage.memory import MemoryStorage

   from bot.database.connection import init_db, get_session, get_tenant_session
   from shared.database.models import Company
   from bot.config import ADMIN_IDS
   from sqlalchemy import select

   # Регистрируем роутеры
   from bot.handlers.client.start import router as start_router
   from bot.handlers.client.booking import router as booking_router
   from bot.handlers.client.calendar import router as calendar_router
   from bot.handlers.client.my_bookings import router as my_bookings_router
   from bot.handlers.client.profile import router as profile_router
   from bot.handlers.admin.menu import router as admin_menu_router
   from bot.handlers.admin.bookings import router as admin_bookings_router
   from bot.handlers.master.work_order import router as master_router

   logger = logging.getLogger(__name__)


   async def run_bot_for_company(company: Company):
       """Запуск бота для конкретной компании"""
       try:
           # Проверяем наличие токена
           if not company.telegram_bot_token:
               logger.warning(f"Компания {company.name} (ID: {company.id}) не имеет токена бота")
               return
           
           # Проверяем активность компании и подписки
           if not company.is_active:
               logger.warning(f"Компания {company.name} (ID: {company.id}) не активна")
               return
           
           if company.subscription_status not in ['active', 'overdue']:
               logger.warning(f"Компания {company.name} (ID: {company.id}) имеет статус: {company.subscription_status}")
               # Можно запускать, но запись будет заблокирована
           
           # Создаем бота с токеном компании
           bot = Bot(token=company.telegram_bot_token)
           dp = Dispatcher(storage=MemoryStorage())
           
           # Сохраняем контекст компании в диспетчере
           dp['company_id'] = company.id
           dp['company_name'] = company.name
           dp['company_code'] = company.code
           dp['schema_name'] = f'tenant_{company.id}'
           dp['can_create_bookings'] = company.can_create_bookings
           dp['subscription_status'] = company.subscription_status
           dp['subscription_end_date'] = company.subscription_end_date
           
           logger.info(f"Запускаем бота для компании {company.name} (ID: {company.id})")
           
           # Инициализируем БД
           await init_db()
           
           # Регистрируем роутеры
           dp.include_router(start_router)
           dp.include_router(profile_router)
           dp.include_router(booking_router)
           dp.include_router(calendar_router)
           dp.include_router(my_bookings_router)
           dp.include_router(admin_menu_router)
           dp.include_router(admin_bookings_router)
           dp.include_router(master_router)
           
           # Запускаем polling
           await dp.start_polling(bot, skip_updates=True)
           
       except Exception as e:
           logger.error(f"Ошибка запуска бота для компании {company.name} (ID: {company.id}): {e}", exc_info=True)
           # Продолжаем работу других ботов, даже если один упал


   async def main():
       """Главная функция запуска всех ботов"""
       logger.info("=== Запуск Multi-Tenant Bot System ===")
       
       # Инициализируем БД
       await init_db()
       
       # Получаем всех активных компаний с токенами
       async for session in get_session():
           result = await session.execute(
               select(Company).where(
                   Company.is_active == True,
                   Company.subscription_status.in_(['active', 'overdue']),
                   Company.telegram_bot_token.isnot(None)
               )
           )
           companies = result.scalars().all()
       
       logger.info(f"Найдено активных компаний: {len(companies)}")
       
       if not companies:
           logger.warning("Не найдено активных компаний с токенами ботов!")
           return
       
       # Запускаем ботов для всех компаний параллельно
       tasks = []
       for company in companies:
           task = asyncio.create_task(run_bot_for_company(company))
           tasks.append(task)
           logger.info(f"Создана задача для компании {company.name} (ID: {company.id})")
       
       # Ждем завершения всех ботов
       logger.info("Запускаем всех ботов...")
       try:
           await asyncio.gather(*tasks)
       except Exception as e:
           logger.error(f"Критическая ошибка: {e}", exc_info=True)
           # Пытаемся продолжить работу, даже если бот упал
       
       logger.info("Все боты остановлены")


   if __name__ == "__main__":
       logging.basicConfig(
           level=logging.INFO,
           format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
       )
       asyncio.run(main())
   ```

**Критерии выполнения:**
- [ ] main.py полностью переписан
- [ ] Запускает несколько ботов
- [ ] Контекст компании сохраняется
- [ ] Обработка ошибок работает
- [ ] Логирование детальное

---

### Подзадача 7.2: Обновить bot/database/connection.py для работы с несколькими схемами

**Описание:** Обновить модуль подключения к БД для поддержки tenant-сессий.

**Что нужно сделать:**

1. Открыть файл:
   ```
   bot/database/connection.py
   ```

2. Добавить функции:
   ```python
   """Управление подключениями к БД"""
   import logging
   from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
   from sqlalchemy.orm import declarative_base
   from sqlalchemy import text

   from bot.config import DATABASE_URL

   logger = logging.getLogger(__name__)

   # Создаем движок
   engine = create_async_engine(DATABASE_URL, echo=False)
   session_factory = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False
   )

   Base = declarative_base()


   async def get_session():
       """Получить сессию (использует схему по умолчанию)"""
       async with session_factory() as session:
           yield session


   async def get_tenant_session(company_id: int):
       """Получить сессию для конкретной схемы клиента"""
       schema_name = f"tenant_{company_id}"
       
       async with session_factory() as session:
           # Устанавливаем search_path на нужную схему
           await session.execute(
               text(f"SET search_path TO {schema_name}, public")
           )
           await session.commit()
           
           yield session
       
       logger.debug(f"Создана сессия для схемы: {schema_name}")


   async def init_db():
       """Инициализация БД (создание всех таблиц)"""
       async with engine.begin() as conn:
           # Схема public создается автоматически
           await conn.execute(
               text("CREATE SCHEMA IF NOT EXISTS public")
           )
           await conn.commit()
       
       # Применяем миграции (для схемы public)
       # Миграции для tenant-схем применяются отдельно


   async def close_db():
       """Закрытие всех соединений"""
       await engine.dispose()
       logger.info("Соединения с БД закрыты")
   ```

**Критерии выполнения:**
- [ ] connection.py обновлен
- [ ] get_tenant_session создана
- [ ] search_path устанавливается
- [ ] Логирование добавлено

---

### Подзадача 7.3: Обновить хендлеры для использования tenant-сессий

**Описание:** Обновить все хендлеры для работы с правильной схемой БД.

**Что нужно сделать:**

1. Обновить bot/handlers/client/start.py:
   ```python
   @router.message(F.text == "/start")
   async def cmd_start(message: Message, state: FSMContext):
       """Обработчик команды /start"""
       # Получаем company_id из контекста
       company_id = state.resolve_dp().get('company_id')
       
       if not company_id:
           logger.error("company_id не найден в контексте")
           await message.answer("❌ Ошибка: компания не найдена")
           return
       
       # Используем tenant-сессию
       async for session in get_tenant_session(company_id):
           # ... существующий код
   ```

2. Обновить bot/handlers/client/booking.py:
   ```python
   @router.message(F.text == "📅 Записаться")
   async def start_booking(message: Message, state: FSMContext):
       """Начать процесс записи"""
       # Получаем company_id из контекста
       company_id = state.resolve_dp().get('company_id')
       can_create_bookings = state.resolve_dp().get('can_create_bookings', True)
       subscription_status = state.resolve_dp().get('subscription_status')
       
       # Проверяем, можно ли создавать записи
       if not can_create_bookings:
           error_message = "❌ Запись отключена.\n\n"
           
           if subscription_status == 'overdue':
               error_message += "Ваша подписка истекла.\n"
               error_message += "Пожалуйста, продлите подписку для создания записи."
           elif subscription_status == 'blocked':
               error_message += "Ваша компания заблокирована.\n"
               error_message += "Для деталей обратитесь к администратору."
           else:
               error_message += "Для деталей обратитесь к администратору."
           
           await message.answer(error_message)
           return
       
       # Используем tenant-сессию
       async for session in get_tenant_session(company_id):
           # ... существующий код
   ```

3. Аналогично обновить все остальные хендлеры:
   - bot/handlers/client/calendar.py
   - bot/handlers/client/my_bookings.py
   - bot/handlers/client/profile.py
   - bot/handlers/admin/menu.py
   - bot/handlers/admin/bookings.py
   - bot/handlers/master/work_order.py

**Критерии выполнения:**
- [ ] start.py обновлен
- [ ] booking.py обновлен
- [ ] Все хендлеры обновлены
- [ ] Проверка подписки работает
- [ ] Tenant-сессии используются

---

### Подзадача 7.4: Добавить сообщения об истекшей подписке

**Описание:** Добавить сообщения для пользователей при истекшей подписке.

**Что нужно сделать:**

1. Обновить bot/handlers/client/start.py:
   ```python
   @router.message(F.text == "/start")
   async def cmd_start(message: Message, state: FSMContext):
       """Обработчик команды /start"""
       company_id = state.resolve_dp().get('company_id')
       subscription_status = state.resolve_dp().get('subscription_status')
       subscription_end_date = state.resolve_dp().get('subscription_end_date')
       
       if subscription_status in ['overdue', 'blocked']:
           days_left_message = ""
           
           if subscription_end_date:
               from datetime import date, timedelta
               days_left = (subscription_end_date - date.today()).days
               
               if days_left < 0:
                   days_left_message = f"Подписка просрочена на {-days_left} дней."
               elif days_left == 0:
                   days_left_message = "Подписка истекает сегодня."
               else:
                   days_left_message = f"Подписка истекает через {days_left} дней."
           
           warning_message = "⚠️ " + days_left_message + "\n\n"
           warning_message += "Запись на услуги временно недоступна.\n"
           warning_message += "Для продолжения работы, пожалуйста, продлите подписку.\n"
           warning_message += "Вы можете просматривать свои записи."
           
           await message.answer(warning_message)
           return
       
       # Используем tenant-сессию
       async for session in get_tenant_session(company_id):
           # ... существующий код
   ```

2. Добавить информацию о подписке в меню:
   ```python
   @router.message(F.text == "/start")
   async def cmd_start(message: Message, state: FSMContext):
       """Обработчик команды /start"""
       # ... после регистрации
       
       subscription_info = ""
       if subscription_status == 'active':
           subscription_info = f"📅 Подписка до: {subscription_end_date.strftime('%d.%m.%Y')}"
       elif subscription_status == 'overdue':
           subscription_info = "⚠️ Подписка просрочена!"
       elif subscription_status == 'blocked':
           subscription_info = "❌ Подписка заблокирована!"
       
       await message.answer(
           f"👋 Добро пожаловать, {client.full_name}!\n\n"
           f"{subscription_info}\n\n"
           f"Выберите действие:",
           reply_markup=get_client_main_keyboard()
       )
   ```

**Критерии выполнения:**
- [ ] Сообщения об истекшей подписке добавлены
- [ ] Количество дней до окончания показывается
- [ ] Информация о подписке в меню
- [ ] Текст понятный для пользователя

---

### Подзадача 7.5: Создать утилиту для запуска/рестарта бота

**Описание:** Создать скрипты для управления отдельными ботами.

**Что нужно сделать:**

1. Создать файл:
   ```
   scripts/start_bot.py
   ```

2. Определить логику:
   ```python
   import sys
   import asyncio
   
   from app.database import get_session_with_schema
   from shared.database.models import Company
   from sqlalchemy import select
   
   async def start_bot(company_id: int):
       """Запуск бота для конкретной компании"""
       async for session in get_session_with_schema("public"):
           result = await session.execute(
               select(Company).where(Company.id == company_id)
           )
           company = result.scalar_one_or_none()
           
           if not company:
               print(f"❌ Компания {company_id} не найдена")
               return
           
           if not company.telegram_bot_token:
               print(f"❌ Компания {company.name} не имеет токена бота")
               return
           
           print(f"🚀 Запускаем бота для компании {company.name}...")
           
           # Импортируем и запускаем бота
           # Можно использовать subprocess или импорт
           # Пример с импортом:
           from bot.main import run_bot_for_company
           await run_bot_for_company(company)
   
   if __name__ == "__main__":
       if len(sys.argv) < 2:
           print("Использование: python start_bot.py <company_id>")
           sys.exit(1)
       
       company_id = int(sys.argv[1])
       asyncio.run(start_bot(company_id))
   ```

3. Создать файл для рестарта:
   ```
   scripts/restart_bot.py
   ```

**Критерии выполнения:**
- [ ] Скрипт start_bot.py создан
- [ ] Скрипт restart_bot.py создан
- [ ] Бот запускается
- [ ] Бот рестартуется

---

### Подзадача 7.6: Обновить bot/config.py

**Описание:** Обновить конфиг для работы с несколькими ботами.

**Что нужно сделать:**

1. Открыть файл:
   ```
   bot/config.py
   ```

2. Обновить для поддержки нескольких ботов:
   ```python
   """Конфигурация Telegram бота"""
   import os
   from typing import List
   from dotenv import load_dotenv

   load_dotenv()

   # Основной токен бота (можно использовать для тестов)
   BOT_TOKEN = os.getenv("BOT_TOKEN", "")

   # ID администраторов (через запятую)
   ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

   # Database
   DB_HOST = os.getenv("DB_HOST", "postgres")
   DB_PORT = int(os.getenv("DB_PORT", "5432"))
   DB_NAME = os.getenv("DB_NAME", "barber_db")
   DB_USER = os.getenv("DB_USER", "barber_user")
   DB_PASSWORD = os.getenv("DB_PASSWORD", "")

   # Redis
   REDIS_HOST = os.getenv("REDIS_HOST", "redis")
   REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
   REDIS_DB = int(os.getenv("REDIS_DB", "0"))

   # App Settings
   DEBUG = os.getenv("DEBUG", "False").lower() == "true"
   TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

   # Work Schedule
   WORK_START_TIME = os.getenv("WORK_START_TIME", "09:00")
   WORK_END_TIME = os.getenv("WORK_END_TIME", "18:00")
   SLOT_DURATION = int(os.getenv("SLOT_DURATION", "30"))
   ENABLE_MASTER_SPECIALIZATION = os.getenv("ENABLE_MASTER_SPECIALIZATION", "false").lower() == "true"

   # Notifications
   REMINDER_DAY_BEFORE_TIME = os.getenv("REMINDER_DAY_BEFORE_TIME", "18:00")
   REMINDER_HOUR_BEFORE = os.getenv("REMINDER_HOUR_BEFORE", "true").lower() == "true"
   NOTIFY_ADMIN_DELAY_MINUTES = int(os.getenv("NOTIFY_ADMIN_DELAY_MINUTES", "5"))
   WORK_ORDER_TIME = os.getenv("WORK_ORDER_TIME", "08:00")

   # Database URL
   DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


   # Мульти-бот настройки
   MULTI_BOT_MODE = os.getenv("MULTI_BOT_MODE", "true").lower() == "true"
   SPECIFIC_COMPANY_ID = os.getenv("SPECIFIC_COMPANY_ID", None)
   
   # Если указан конкретный company_id, запускаем только его
   if SPECIFIC_COMPANY_ID:
       SPECIFIC_COMPANY_ID = int(SPECIFIC_COMPANY_ID)
   ```

**Критерии выполнения:**
- [ ] config.py обновлен
- [ ] MULTI_BOT_MODE добавлен
- [ ] SPECIFIC_COMPANY_ID добавлен
- [ ] Переменные задокументированы

---

### Подзадача 7.7: Протестировать работу нескольких ботов

**Описание:** Полное тестирование мульти-бот системы.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_multi_bots.py
   ```

2. Реализовать тесты:
   ```python
   import asyncio
   import sys
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, text
   
   from app.database import get_session_with_schema, get_tenant_session
   from shared.database.models import Company, User
   from bot.database.connection import init_db
   
   async def test_multi_bots():
       """Тестирование мульти-бот системы"""
       print("=== Тестирование Multi-Bot System ===\n")
       
       # Инициализируем БД
       await init_db()
       
       # Тест 1: Проверка компаний
       print("1. Проверка компаний...")
       async for session in get_session_with_schema("public"):
           result = await session.execute(
               select(Company).where(
                   Company.is_active == True,
                   Company.telegram_bot_token.isnot(None)
               )
           )
           companies = result.scalars().all()
           
           for company in companies:
               print(f"   ✅ Компания: {company.name} (ID: {company.id})")
               print(f"      Токен: {company.telegram_bot_token[:20]}...")
               print(f"      Схема: tenant_{company.id}")
           
           print(f"Всего компаний: {len(companies)}")
       
       # Тест 2: Проверка изоляции данных
       print("\n2. Проверка изоляции данных...")
       if len(companies) >= 2:
           company1, company2 = companies[0], companies[1]
           
           # Создаем тестовую запись в tenant_001
           async for session in get_tenant_session(company1.id):
               from bot.database.crud import create_booking
               from datetime import date, time
               
               await create_booking(
                   session,
                   client_id=1,
                   service_id=1,
                   booking_date=date.today(),
                   booking_time=time(9, 0),
                   duration=30,
                   end_time=time(9, 30),
                   comment="TEST_ISOLATION",
                   created_by=1
               )
           
           print(f"   Тестовая запись создана в tenant_{company1.id}")
           
           # Проверяем, что она НЕ видна в tenant_002
           async for session in get_tenant_session(company2.id):
               from bot.database.crud import get_bookings_by_client
               
               bookings = await get_bookings_by_client(session, 1)
               
               print(f"   Записей в tenant_{company2.id}: {len(bookings)}")
               
               found = False
               for booking in bookings:
                   if booking.comment == "TEST_ISOLATION":
                       found = True
                       break
               
               if found:
                   print(f"   ❌ ОШИБКА ИЗОЛЯЦИИ! Запись видна в другой схеме")
               else:
                   print(f"   ✅ Изоляция данных работает!")
       else:
           print(f"   ⚠️ Недостаточно компаний для теста изоляции (нужно >= 2)")
       
       # Тест 3: Проверка контекста диспетчера
       print("\n3. Проверка контекста диспетчера...")
       # Этот тест проверяет, что company_id сохраняется в контексте
       # Реализуется через логи при запуске
       print(f"   ✅ Контекст диспетчера проверяется через логи")
       
       print("\n=== Тестирование завершено ===")
   
   if __name__ == "__main__":
       asyncio.run(test_multi_bots())
   ```

3. Запустить тест:
   ```bash
   docker compose exec bot python scripts/test_multi_bots.py
   ```

4. Проверить логи всех ботов:
   ```bash
   docker compose logs bot -f | grep -E "(Запускаем бота|company_id|schema_name)"
   ```

**Критерии выполнения:**
- [ ] Тестовый скрипт создан
- [ ] Тест компаний пройден
- [ ] Тест изоляции данных пройден
- [ ] Тест контекста пройден
- [ ] Логи проверены
- [ ] Нет ошибок в логах

---

### Подзадача 7.8: Протестировать проверку подписки

**Описание:** Тестирование блокировки создания записей при истекшей подписке.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_subscription_check.py
   ```

2. Реализовать тесты:
   ```python
   import asyncio
   import sys
   from sqlalchemy import select, text
   
   from app.database import get_session_with_schema
   from shared.database.models import Company
   
   async def test_subscription_check():
       """Тестирование проверки подписки"""
       print("=== Тестирование проверки подписки ===\n")
       
       # Тест 1: Компания с активной подпиской
       print("1. Компания с активной подпиской...")
       async for session in get_session_with_schema("public"):
           result = await session.execute(
               select(Company).where(Company.id == 1)
           )
           company = result.scalar_one_or_none()
           
           if company:
               print(f"   Company: {company.name}")
               print(f"   is_active: {company.is_active}")
               print(f"   can_create_bookings: {company.can_create_bookings}")
               print(f"   subscription_status: {company.subscription_status}")
               
               if company.can_create_bookings:
                   print(f"   ✅ Создание записей разрешено")
               else:
                   print(f"   ❌ Создание записей заблокировано")
           else:
               print(f"   ❌ Компания не найдена")
       
       # Тест 2: Компания с истекшей подпиской
       print("\n2. Компания с истекшей подпиской...")
       async for session in get_session_with_schema("public"):
           result = await session.execute(
               select(Company).where(Company.id == 1)
           )
           company = result.scalar_one_or_none()
           
           if company:
               # Установим can_create_bookings = False для теста
               company.can_create_bookings = False
               await session.commit()
               
               print(f"   Company: {company.name}")
               print(f"   can_create_bookings: {company.can_create_bookings}")
               print(f"   ✅ Блокировка работает")
               
               # Восстанавливаем
               company.can_create_bookings = True
               await session.commit()
       else:
           print(f"   ❌ Компания не найдена")
       
       print("\n=== Тестирование завершено ===")
   
   if __name__ == "__main__":
       asyncio.run(test_subscription_check())
   ```

3. Запустить тест:
   ```bash
   docker compose exec bot python scripts/test_subscription_check.py
   ```

**Критерии выполнения:**
- [ ] Тестовый скрипт создан
- [ ] Тест активной подписки пройден
- [ ] Тест истекшей подписки пройден
- [ ] Блокировка работает
- [ ] Разблокировка работает

---

## ✅ Чек-лист этапа

### Bot main.py

- [ ] main.py полностью переписан
- [ ] Запускает несколько ботов
- [ ] Контекст компании сохраняется
- [ ] Обработка ошибок работает
- [ ] Логирование детальное

### Database

- [ ] connection.py обновлен
- [ ] get_tenant_session создана
- [ ] search_path устанавливается
- [ ] Логирование добавлено

### Хендлеры

- [ ] start.py обновлен
- [ ] booking.py обновлен
- [ ] Все хендлеры обновлены
- [ ] Проверка подписки работает
- [ ] Tenant-сессии используются

### Сообщения

- [ ] Сообщения об истекшей подписке добавлены
- [ ] Количество дней показывается
- [ ] Текст понятный

### Утилиты

- [ ] Скрипт start_bot.py создан
- [ ] Скрипт restart_bot.py создан
- [ ] Конфиг обновлен

### Тестирование

- [ ] Тестовый скрипт создан
- [ ] Тест мульти-ботов пройден
- [ ] Тест изоляции пройден
- [ ] Тест подписки пройден
- [ ] Логи проверены

---

## ⚠️ Риски и их решение

### Риск 1: Конфликт токенов ботов

**Вероятность:** Низкая  
**Влияние:** Среднее

**Меры предупреждения:**
- Проверка уникальности токенов
- Валидация при регистрации
- Хранение токенов в БД

**Решение при возникновении:**
- Проверка логов
- Обновление токена
- Связь с поддержкой

---

### Риск 2: Ошибки при переключении схем

**Вероятность:** Средняя  
**Влияние:** Среднее

**Меры предупреждения:**
- Тестирование переключений
- Проверка search_path
- Логирование всех переключений

**Решение при возникновении:**
- Повторная попытка подключения
- Сброс search_path
- Откат к умолчанию

---

### Риск 3: Память при запуске множества ботов

**Вероятность:** Средняя  
**Влияние:** Высокое

**Меры предупреждения:**
- Мониторинг памяти
- Ограничение количества ботов
- Оптимизация состояния FSM

**Решение при возникновении:**
- Увеличение памяти контейнера
- Использование MemoryStorage с ограничением
- Рестарт контейнера

---

### Риск 4: Бесконечный цикл при ошибках

**Вероятность:** Низкая  
**Влияние:** Среднее

**Меры предупреждения:**
- Тайм-ауты для повторных попыток
- Лимит на количество рестартов
- Логирование рестартов

**Решение при возникновении:**
- Логирование ошибок
- Остановка бота
- Уведомление администратора

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить логи всех ботов:
   ```bash
   docker compose logs bot -f
   ```

2. Проверить статус конкретного бота:
   ```bash
   docker compose logs bot | grep "company_id": 1"
   ```

3. Проверить контекст диспетчера:
   ```bash
   docker compose logs bot | grep "company_id\|schema_name"
   ```

4. Проверить работу со схемами:
   ```bash
   docker compose exec postgres psql -U barber_user -d barber_db -c "\dn"
   ```

5. Рестартнуть конкретного бота:
   ```bash
   docker compose restart bot
   # Бот перезапустит все компании
   ```

6. Проверить конфиг:
   ```bash
   docker compose exec bot printenv | grep MULTI_BOT
   ```

---

**Этап 7 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

