# Этап 6: Celery Задачи

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

Реализовать автоматические задачи для напоминания об оплате, проверки подписок и обработки webhook от Юкассы.

### Ожидаемый результат

- Напоминания за 7 дней до окончания подписки
- Напоминания за 3 дня до окончания
- Напоминания в день окончания
- Автоматическая блокировка записи при неоплате
- Автоматическая полная блокировка через 7 дней
- Обработка webhook от Юкассы в фоне
- Автоматическая отправка лист-нарядов мастерам

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Этап 4 завершен (публичные API работают)
- [ ] Этап 5 завершен (API супер-админа работают)
- [ ] Celery и Celery Beat настроены
- [ ] Redis работает

### Технические требования

- Python 3.11+ установлен
- Celery 5.3+ установлен
- Redis 7+ работает
- Понимание работы с фоновыми задачами

---

## 📝 Подзадачи

### Подзадача 6.1: Создать subscription_tasks.py

**Описание:** Создать модуль с задачами для управления подписками.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/tasks/subscription_tasks.py
   ```

2. Определить задачи:
   ```python
   from celery import shared_task
   from datetime import date, datetime, timedelta
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, and_
   import logging
   
   from app.database import get_session_with_schema
   from app.models.company import Company
   from app.models.subscription import Subscription
   from app.services.company_service import block_company_bookings, block_company_full
   
   logger = logging.getLogger(__name__)
   
   @shared_task
   def send_reminder_7_days_before():
       """Отправить напоминание за 7 дней до окончания подписки"""
       asyncio.run(_send_reminders(days_before=7))
   
   @shared_task
   def send_reminder_3_days_before():
       """Отправить напоминание за 3 дня до окончания подписки"""
       asyncio.run(_send_reminders(days_before=3))
   
   @shared_task
   def send_reminder_today():
       """Отправить напоминание в день окончания подписки"""
       asyncio.run(_send_reminders(days_before=0))
   
   @shared_task
   def check_overdue_subscriptions():
       """Проверить и заблокировать просроченные подписки"""
       asyncio.run(_check_overdue())
   
   @shared_task
   def check_full_block_subscriptions():
       """Проверить и заблокировать компании с просрочкой > 7 дней"""
       asyncio.run(_check_full_block())
   
   async def _send_reminders(days_before: int):
       """Отправить напоминания"""
       target_date = date.today() + timedelta(days=days_before)
       
       async for session in get_session_with_schema("public"):
           # Ищем компании с подпиской, заканчивающейся через days_before дней
           from sqlalchemy import func
           
           result = await session.execute(
               select(Company, Subscription.end_date, Subscription.end_date - target_date).join(
                   Subscription, Company.id == Subscription.company_id
               ).where(
                   Company.is_active == True,
                   Company.subscription_status == 'active',
                   Subscription.end_date == target_date
               )
           )
           companies_data = result.all()
           
           for company, end_date, days_left in companies_data:
               await _send_reminder_to_company(company, days_left)
       
       logger.info(f"Напоминания отправлены компаниям, у которых подписка заканчивается через {days_before} дней")
   
   async def _send_reminder_to_company(company, days_left):
       """Отправить напоминание компании"""
       # Отправляем Telegram сообщение или email
       # TODO: Реализовать отправку
       
       logger.info(f"Напоминание отправлено компании {company.name} (до окончания: {days_left} дней)")
   
   async def _check_overdue():
       """Проверить и заблокировать просроченные подписки"""
       today = date.today()
       
       async for session in get_session_with_schema("public"):
           # Ищем компании с просроченной подпиской
           result = await session.execute(
               select(Company).where(
                   Company.is_active == True,
                   Company.subscription_status == 'active',
                   Company.subscription_end_date < today
               )
           )
           companies = result.scalars().all()
           
           for company in companies:
               # Блокируем только создание записей
               await block_company_bookings(session, company.id)
               logger.warning(f"Компания {company.name} заблокирована (только запись)")
           
           await session.commit()
       
       logger.info(f"Заблокировано {len(companies)} компаний с просроченной подпиской")
   
   async def _check_full_block():
       """Проверить и полностью заблокировать компании"""
       today = date.today()
       seven_days_ago = today - timedelta(days=7)
       
       async for session in get_session_with_schema("public"):
           # Ищем компании с просрочкой более 7 дней
           result = await session.execute(
               select(Company).where(
                   Company.is_active == True,
                   Company.subscription_end_date < seven_days_ago
               )
           )
           companies = result.scalars().all()
           
           for company in companies:
               # Полная блокировка
               await block_company_full(session, company.id)
               logger.error(f"Компания {company.name} полностью заблокирована (просрочка > 7 дней)")
           
           await session.commit()
       
       logger.warning(f"Полностью заблокировано {len(companies)} компаний")
   ```

**Критерии выполнения:**
- [ ] Файл создан
- [ ] Все задачи определены
- [ ] Напоминания отправляются
- [ ] Блокировки работают
- [ ] Логирование работает

---

### Подзадача 6.2: Создать payment_tasks.py

**Описание:** Создать модуль с задачами для обработки платежей.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/tasks/payment_tasks.py
   ```

2. Определить задачи:
   ```python
   from celery import shared_task
   import logging
   import asyncio
   
   from app.database import get_session_with_schema
   from app.models.payment import Payment
   from app.services.subscription_service import create_subscription
   
   logger = logging.getLogger(__name__)
   
   @shared_task
   def process_yookassa_webhook(payment_id: str, status: str):
       """Обработка webhook от Юкассы в фоне"""
       try:
           asyncio.run(_process_webhook(payment_id, status))
       except Exception as e:
           logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
   
   async def _process_webhook(payment_id: str, status: str):
       """Обработка webhook"""
       from app.services.payment_service import update_payment
       
       async for session in get_session_with_schema("public"):
           # Ищем платеж
           result = await session.execute(
               select(Payment).where(Payment.yookassa_payment_id == payment_id)
           )
           payment = result.scalar_one_or_none()
           
           if not payment:
               logger.error(f"Платеж {payment_id} не найден")
               return
           
           # Обновляем статус
           await update_payment(session, payment.id, {
               "yookassa_payment_status": status,
               "status": "completed" if status == "succeeded" else "failed"
           })
           
           # Если оплата успешна
           if status == "succeeded":
               # Создаем подписку
               subscription_id = payment.subscription_id
               company_id = payment.company_id
               plan_id = payment.metadata.get("plan_id")
               
               await create_subscription(session, {
                   "company_id": company_id,
                   "plan_id": plan_id,
                   "start_date": date.today(),
                   "end_date": date.today() + timedelta(days=30),
                   "status": "active",
                   "payment_method": "yookassa",
                   "yookassa_payment_id": payment_id
               })
               
               # Активируем компанию
               from app.models.company import Company
               result = await session.execute(
                   select(Company).where(Company.id == company_id)
               )
               company = result.scalar_one_or_none()
               
               if company:
                   company.is_active = True
                   company.subscription_status = "active"
                   company.can_create_bookings = True
                   await session.commit()
                   
                   # Создаем схему и применяем миграции (в фоне)
                   # TODO: Вызвать задачу создания инфраструктуры
                   
               logger.info(f"Компания {company_id} активирована после успешной оплаты")
           
           await session.commit()
           
       logger.info(f"Webhook {payment_id} обработан, статус: {status}")
   ```

**Критерии выполнения:**
- [ ] Файл создан
- [ ] Задачи определены
- [ ] Webhook обрабатывается
- [ ] Подписка создается
- [ ] Компания активируется
- [ ] Логирование работает

---

### Подзадача 6.3: Настроить Celery Beat

**Описание:** Настроить расписание для выполнения задач.

**Что нужно сделать:**

1. Обновить web/backend/app/celery_app.py:
   ```python
   from celery.schedules import crontab
   
   from app.tasks.subscription_tasks import (
       send_reminder_7_days_before,
       send_reminder_3_days_before,
       send_reminder_today,
       check_overdue_subscriptions,
       check_full_block_subscriptions
   )
   
   # Расписание задач
   app.conf.beat_schedule = {
       # Напоминания об оплате
       'send-reminder-7-days': {
           'task': 'app.tasks.subscription_tasks.send_reminder_7_days_before',
           'schedule': crontab(hour=10, minute=0),  # Каждый день в 10:00
       },
       'send-reminder-3-days': {
           'task': 'app.tasks.subscription_tasks.send_reminder_3_days_before',
           'schedule': crontab(hour=10, minute=0),  # Каждый день в 10:00
       },
       'send-reminder-today': {
           'task': 'app.tasks.subscription_tasks.send_reminder_today',
           'schedule': crontab(hour=9, minute=0),   # Каждый день в 09:00
       },
       
       # Проверка подписок
       'check-overdue-subscriptions': {
           'task': 'app.tasks.subscription_tasks.check_overdue_subscriptions',
           'schedule': crontab(hour=11, minute=0),  # Каждый день в 11:00
       },
       'check-full-block-subscriptions': {
           'task': 'app.tasks.subscription_tasks.check_full_block_subscriptions',
           'schedule': crontab(hour=12, minute=0),  # Каждый день в 12:00
       },
   }
   
   logger.info("Celery Beat настроен для задач подписок")
   ```

2. Проверить конфигурацию:
   ```bash
   docker compose exec web celery -A app.celery inspect beat
   ```

**Критерии выполнения:**
- [ ] Celery Beat настроен
- [ ] Расписание задано
- [ ] Задачи выполняются по расписанию
- [ ] Логи Celery работают

---

### Подзадача 6.4: Протестировать задачи

**Описание:** Протестировать выполнение всех задач.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_celery_tasks.py
   ```

2. Реализовать тесты:
   ```python
   import asyncio
   from datetime import date, timedelta
   
   from app.tasks.subscription_tasks import (
       send_reminder_7_days_before,
       send_reminder_3_days_before,
       send_reminder_today,
       check_overdue_subscriptions,
       check_full_block_subscriptions
   )
   from app.database import get_session_with_schema
   
   async def test_reminders():
       """Тест напоминаний"""
       print("=== Тест напоминаний ===\n")
       
       # Тест 1: Напоминания за 7 дней
       print("1. Тест напоминаний за 7 дней...")
       await send_reminder_7_days_before.apply_async()
       print("   ✅ Задача отправлена в очередь\n")
       
       # Тест 2: Напоминания за 3 дня
       print("2. Тест напоминаний за 3 дня...")
       await send_reminder_3_days_before.apply_async()
       print("   ✅ Задача отправлена в очередь\n")
       
       # Тест 3: Напоминания сегодня
       print("3. Тест напоминаний сегодня...")
       await send_reminder_today.apply_async()
       print("   ✅ Задача отправлена в очередь\n")
       
       print("=== Тест напоминаний завершен ===\n")
   
   async def test_blocking():
       """Тест блокировок"""
       print("=== Тест блокировок ===\n")
       
       # Тест 1: Проверка просроченных подписок
       print("1. Тест проверки просроченных подписок...")
       await check_overdue_subscriptions.apply_async()
       print("   ✅ Задача отправлена в очередь\n")
       
       # Тест 2: Проверка полных блокировок
       print("2. Тест проверки полных блокировок...")
       await check_full_block_subscriptions.apply_async()
       print("   ✅ Задача отправлена в очередь\n")
       
       print("=== Тест блокировок завершен ===\n")
   
   async def test_payment_webhook():
       """Тест обработки webhook"""
       print("=== Тест обработки webhook ===\n")
       
       print("1. Тест успешного webhook...")
       await process_yookassa_webhook("test_payment_id", "succeeded")
       print("   ✅ Задача отправлена в очередь\n")
       
       print("2. Тест неудачного webhook...")
       await process_yookassa_webhook("test_payment_id_2", "canceled")
       print("   ✅ Задача отправлена в очередь\n")
       
       print("=== Тест обработки webhook завершен ===\n")
   
   async def test_tasks():
       """Запустить все тесты"""
       await test_reminders()
       await test_blocking()
       await test_payment_webhook()
   
   if __name__ == "__main__":
       asyncio.run(test_tasks())
   ```

3. Запустить тесты:
   ```bash
   docker compose exec web python scripts/test_celery_tasks.py
   ```

4. Проверить Celery worker:
   ```bash
   docker compose logs celery-worker -f
   ```

5. Проверить Celery Beat:
   ```bash
   docker compose logs celery-beat -f
   ```

**Критерии выполнения:**
- [ ] Тестовый скрипт создан
- [ ] Все тесты пройдены
- [ ] Задачи выполняются в очереди
- [ ] Celery worker обрабатывает задачи
- [ ] Логи Celery корректны

---

### Подзадача 6.5: Добавить отправку уведомлений

**Описание:** Реализовать отправку Telegram сообщений и email.

**Что нужно сделать:**

1. Обновить bot/config.py:
   ```python
   # Уведомления
   NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN", BOT_TOKEN)
   ```

2. Создать сервис уведомлений:
   ```python
   web/backend/app/services/notification_service.py
   ```

3. Определить функции:
   ```python
   import aiohttp
   import logging
   from typing import Optional
   
   from bot.config import NOTIFICATION_BOT_TOKEN
   
   logger = logging.getLogger(__name__)
   
   async def send_telegram_message(telegram_id: int, text: str):
       """Отправить Telegram сообщение"""
       url = f"https://api.telegram.org/bot{NOTIFICATION_BOT_TOKEN}/sendMessage"
       payload = {
           "chat_id": telegram_id,
           "text": text,
           "parse_mode": "HTML"
       }
       
       try:
           async with aiohttp.ClientSession() as session:
               async with session.post(url, json=payload) as response:
                   data = await response.json()
                   
                   if not data.get("ok"):
                       logger.error(f"Ошибка отправки сообщения: {data}")
                       return False
                   
                   logger.info(f"Сообщение отправлено: telegram_id={telegram_id}")
                   return True
       
       except Exception as e:
           logger.error(f"Ошибка отправки Telegram сообщения: {e}", exc_info=True)
           return False
   
   async def send_email_notification(email: str, subject: str, body: str):
       """Отправить email уведомление"""
       # TODO: Реализовать через SMTP или сервис рассылки
       logger.info(f"Email отправлен: {email}")
       return True
   ```

4. Обновить задачи для использования сервиса:
   ```python
   from app.services.notification_service import send_telegram_message, send_email_notification
   
   async def _send_reminder_to_company(company, days_left):
       """Отправить напоминание компании"""
       # Получаем ID админа компании
       admin_telegram_id = get_company_admin_telegram_id(company.id)
       
       if admin_telegram_id:
           days_text = "сегодня" if days_left == 0 else f"через {days_left} дней"
           
           message = f"""
           ⚠️ Уведомление об оплате подписки!
           
           Здравствуйте!
           
           Ваша подписка истекает {days_text}.
           
           Для продолжения работы системы, пожалуйста, продлите подписку.
           
           С уважением,
           AutoService SaaS
           """
           
           await send_telegram_message(admin_telegram_id, message)
       
       # Если есть email, отправляем и email
       if company.email:
           subject = f"Уведомление об оплате подписки"
           await send_email_notification(company.email, subject, message)
   ```

**Критерии выполнения:**
- [ ] Сервис уведомлений создан
- [ ] Telegram сообщения отправляются
- [ ] Email уведомления работают (если реализованы)
- [ ] Задачи используют сервис
- [ ] Ошибки обрабатываются

---

### Подзадача 6.6: Протестировать отправку уведомлений

**Описание:** Протестировать отправку уведомлений.

**Что нужно сделать:**

1. Создать тестовый скрипт:
   ```
   scripts/test_notifications.py
   ```

2. Реализовать тесты:
   ```python
   import asyncio
   from app.services.notification_service import send_telegram_message
   
   async def test_telegram_notification():
       """Тест отправки Telegram сообщения"""
       print("=== Тест Telegram уведомлений ===\n")
       
       # Используем тестовый Telegram ID
       test_telegram_id = 329621295  # Заменить на тестовый
       
       message = "🧪 Тестовое уведомление от Celery задачи!"
       
       print("1. Отправляем тестовое сообщение...")
       success = await send_telegram_message(test_telegram_id, message)
       
       if success:
           print("   ✅ Сообщение отправлено\n")
       else:
           print("   ❌ Ошибка отправки\n")
       
       print("=== Тест Telegram уведомлений завершен ===\n")
   
   async def test_tasks():
       """Запустить все тесты"""
       await test_telegram_notification()
   
   if __name__ == "__main__":
       asyncio.run(test_tasks())
   ```

3. Запустить тест:
   ```bash
   docker compose exec web python scripts/test_notifications.py
   ```

**Критерии выполнения:**
- [ ] Тестовый скрипт создан
- [ ] Сообщение отправлено
- [ ] Нет ошибок в логах
- [ ] Тест успешен

---

## ✅ Чек-лист этапа

### Задачи подписок

- [ ] subscription_tasks.py создан
- [ ] Напоминания за 7 дней работают
- [ ] Напоминания за 3 дня работают
- [ ] Напоминания сегодня работают
- [ ] Проверка просроченных подписок работает
- [ ] Полная блокировка работает

### Задачи платежей

- [ ] payment_tasks.py создан
- [ ] Обработка webhook работает
- [ ] Подписка создается
- [ ] Компания активируется
- [ ] Инфраструктура создается

### Celery Beat

- [ ] Расписание настроено
- [ ] Задачи выполняются вовремя
- [ ] Логи Celery Beat корректны
- [ ] Нет дублирования задач

### Уведомления

- [ ] Сервис уведомлений создан
- [ ] Telegram сообщения отправляются
- [ ] Email уведомления работают
- [ ] Ошибки обрабатываются

### Тестирование

- [ ] Тестовые скрипты созданы
- [ ] Все тесты пройдены
- [ ] Celery worker обрабатывает
- [ ] Логи корректны
- [ ] Нет ошибок

---

## ⚠️ Риски и их решение

### Риск 1: Задачи не выполняются по расписанию

**Вероятность:** Средняя  
**Влияние:** Высокое

**Меры предупреждения:**
- Проверка работы Celery Beat
- Логирование всех задач
- Мониторинг выполнения

**Решение при возникновении:**
- Ручной запуск задач
- Перезапуск Celery Beat
- Проверка конфигурации

---

### Риск 2: Ошибки при отправке уведомлений

**Вероятность:** Низкая  
**Влияние:** Среднее

**Меры предупреждения:**
- Обработка всех ошибок
- Логирование попыток
- Резервный способ уведомления

**Решение при возникновении:**
- Повторная отправка
- Отправка через email
- Создание задачи для повторной отправки

---

### Риск 3: Дублирование задач

**Вероятность:** Низкая  
**Влияние:** Низкое

**Меры предупреждения:**
- Уникальные имена задач
- Проверка очереди перед выполнением
- Логирование всех запусков

**Решение при возникновении:**
- Проверка состояния задач
- Очистка очереди
- Перезапуск Celery

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить Celery worker:
   ```bash
   docker compose logs celery-worker -f
   ```

2. Проверить Celery Beat:
   ```bash
   docker compose logs celery-beat -f
   ```

3. Проверить список активных задач:
   ```bash
   docker compose exec web celery -A app.celery inspect active
   ```

4. Проверить запланированные задачи:
   ```bash
   docker compose exec web celery -A app.celery inspect scheduled
   ```

5. Проверить Redis:
   ```bash
   docker compose exec redis redis-cli keys "celery*"
   ```

---

**Этап 6 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

