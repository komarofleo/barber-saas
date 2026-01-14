# Этап 5: Backend - API для супер-админа

**Продолжительность:** 2 дня  
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

Реализовать API для супер-админа для управления всеми клиентами, подписками и платежами.

### Ожидаемый результат

- API для управления компаниями
- API для управления подписками
- API для просмотра статистики биллинга
- API для просмотра платежей
- Экспорт данных в Excel
- Проверка прав супер-админа

---

## 🔧 Предварительные требования

### Перед началом работы

- [ ] Этап 2 завершен (модели и схемы созданы)
- [ ] Этап 4 завершен (публичные API работают)
- [ ] Супер-админ создан через скрипт
- [ ] Понимание требований к статистике биллинга

### Технические требования

- Python 3.11+ установлен
- Все зависимости установлены
- Доступ к базе данных
- Понимание работы с pandas (для экспорта в Excel)

---

## 📝 Подзадачи

### Подзадача 5.1: Создать super_admin.py API модуль

**Описание:** Создать новый модуль API для управления супер-админ функционалом.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/api/super_admin.py
   ```

2. Определить роутер:
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, func
   from typing import Optional, List
   from datetime import date, datetime, timedelta

   router = APIRouter(prefix="/api/super-admin", tags=["super_admin"])
   ```

**Критерии выполнения:**
- [ ] Модуль создан
- [ ] Роутер определен
- [ ] Префикс /api/super-admin
- [ ] Тег "super_admin" добавлен

---

### Подзадача 5.2: Реализовать статистику дашборда

**Описание:** Создать endpoint с общей статистикой по всем клиентам.

**Что нужно сделать:**

1. Определить Pydantic схему:
   ```python
   class DashboardStatsResponse(BaseModel):
       total_companies: int
       active_companies: int
       overdue_companies: int
       blocked_companies: int
       total_revenue_all_time: Decimal
       revenue_this_month: Decimal
       revenue_today: Decimal
       total_payments: int
       new_companies_this_month: int
       total_users: int
       total_bookings: int
   
       class Config:
           from_attributes = True
   ```

2. Реализовать endpoint:
   ```python
   @router.get("/dashboard/stats", response_model=DashboardStatsResponse)
   async def get_dashboard_stats(
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Получить статистику дашборда супер-админа"""
       
       # Общее количество компаний
       total_companies = await db.scalar(
           select(func.count(Company.id))
       ) or 0
       
       # Активные компании
       active_companies = await db.scalar(
           select(func.count(Company.id)).where(
               Company.is_active == True,
               Company.subscription_status == 'active'
           )
       ) or 0
       
       # Просроченные компании
       overdue_companies = await db.scalar(
           select(func.count(Company.id)).where(
               Company.is_active == True,
               Company.subscription_status == 'overdue'
           )
       ) or 0
       
       # Заблокированные компании
       blocked_companies = await db.scalar(
           select(func.count(Company.id)).where(
               Company.is_active == False
           )
       ) or 0
       
       # Общая выручка (все время)
       total_revenue_all_time = await db.scalar(
           select(func.sum(Payment.amount)).where(Payment.status == 'completed')
       ) or Decimal('0.00')
       
       # Выручка за этот месяц
       first_day_month = date.today().replace(day=1)
       revenue_this_month = await db.scalar(
           select(func.sum(Payment.amount)).where(
               Payment.status == 'completed',
               Payment.payment_date >= first_day_month
           )
       ) or Decimal('0.00')
       
       # Выручка сегодня
       today = date.today()
       revenue_today = await db.scalar(
           select(func.sum(Payment.amount)).where(
               Payment.status == 'completed',
               Payment.payment_date >= today
           )
       ) or Decimal('0.00')
       
       # Общее количество платежей
       total_payments = await db.scalar(
           select(func.count(Payment.id))
       ) or 0
       
       # Новые компании за месяц
       new_companies_this_month = await db.scalar(
           select(func.count(Company.id)).where(
               Company.created_at >= first_day_month
           )
       ) or 0
       
       # Общее количество пользователей (сумма по всем компаниям)
       # Это сложнее, можно упростить или оставить None
       total_users = None  # TODO: посчитать через JOIN с tenant-схемами
       
       # Общее количество записей (аналогично)
       total_bookings = None  # TODO: посчитать через JOIN с tenant-схемами
       
       return DashboardStatsResponse(
           total_companies=total_companies,
           active_companies=active_companies,
           overdue_companies=overdue_companies,
           blocked_companies=blocked_companies,
           total_revenue_all_time=total_revenue_all_time,
           revenue_this_month=revenue_this_month,
           revenue_today=revenue_today,
           total_payments=total_payments,
           new_companies_this_month=new_companies_this_month,
           total_users=total_users,
           total_bookings=total_bookings
       )
   ```

**Критерии выполнения:**
- [ ] Endpoint создан
- [ ] Статистика считается корректно
- [ ] Выручка считается верно
- [ ] Количество компаний верно
- [ ] Только супер-админ может получить статистику

---

### Подзадача 5.3: Реализовать API компаний

**Описание:** Создать CRUD endpoints для управления компаниями.

**Что нужно сделать:**

1. Создать endpoint для списка компаний:
   ```python
   @router.get("/companies")
   async def get_companies(
       page: int = Query(1, ge=1),
       page_size: int = Query(20, ge=1, le=100),
       is_active: Optional[bool] = None,
       subscription_status: Optional[str] = None,
       search: Optional[str] = None,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Получить список компаний"""
       query = select(Company)
       
       conditions = []
       if is_active is not None:
           conditions.append(Company.is_active == is_active)
       if subscription_status is not None:
           conditions.append(Company.subscription_status == subscription_status)
       if search:
           search_term = f"%{search}%"
           conditions.append(Company.name.ilike(search_term))
       
       if conditions:
           query = query.where(and_(*conditions))
       
       # Общее количество
       count_query = select(func.count(Company.id))
       if conditions:
           count_query = count_query.where(and_(*conditions))
       
       total = await db.scalar(count_query) or 0
       
       # Пагинация
       query = query.offset((page - 1) * page_size).limit(page_size)
       query = query.order_by(Company.created_at.desc())
       
       result = await db.execute(query)
       companies = result.scalars().all()
       
       return {
           "items": companies,
           "total": total,
           "page": page,
           "page_size": page_size
       }
   ```

2. Создать endpoint для получения компании:
   ```python
   @router.get("/companies/{company_id}")
   async def get_company(
       company_id: int,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Получить информацию о компании"""
       from sqlalchemy.orm import selectinload
       
       query = select(Company).options(
           selectinload(Company.subscriptions),
           selectinload(Company.payments)
       ).where(Company.id == company_id)
       
       result = await db.execute(query)
       company = result.scalar_one_or_none()
       
       if not company:
           raise HTTPException(status_code=404, detail="Компания не найдена")
       
       return company
   ```

3. Создать endpoint для блокировки компании:
   ```python
   @router.patch("/companies/{company_id}/block")
   async def block_company(
       company_id: int,
       block_type: str = Body(..., embed=True, description="Тип блокировки: bookings_only или full"),
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Заблокировать компанию"""
       
       result = await db.execute(
           select(Company).where(Company.id == company_id)
       )
       company = result.scalar_one_or_none()
       
       if not company:
           raise HTTPException(status_code=404, detail="Компания не найдена")
       
       if block_type.block_type == "bookings_only":
           # Блокируем только создание записей
           company.can_create_bookings = False
           company.subscription_status = 'overdue'
       elif block_type.block_type == "full":
           # Полная блокировка
           company.is_active = False
           company.subscription_status = 'blocked'
       else:
           raise HTTPException(
               status_code=400,
               detail="Неверный тип блокировки. Используйте: bookings_only или full"
           )
       
       await db.commit()
       await db.refresh(company)
       
       return {
           "status": "success",
           "message": f"Компания {company.name} заблокирована",
           "block_type": block_type.block_type
       }
   ```

4. Создать endpoint для разблокировки:
   ```python
   @router.patch("/companies/{company_id}/unblock")
   async def unblock_company(
       company_id: int,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Разблокировать компанию"""
       
       result = await db.execute(
           select(Company).where(Company.id == company_id)
       )
       company = result.scalar_one_or_none()
       
       if not company:
           raise HTTPException(status_code=404, detail="Компания не найдена")
       
       company.is_active = True
       company.can_create_bookings = True
       company.subscription_status = 'active'
       
       await db.commit()
       await db.refresh(company)
       
       return {
           "status": "success",
           "message": f"Компания {company.name} разблокирована"
       }
   ```

**Критерии выполнения:**
- [ ] Список компаний работает
- [ ] Фильтры работают
- [ ] Пагинация работает
- [ ] Получение компании работает
- [ ] Блокировка работает (bookings_only)
- [ ] Полная блокировка работает
- [ ] Разблокировка работает

---

### Подзадача 5.4: Реализовать API биллинга

**Описание:** Создать endpoints для статистики платежей и их просмотра.

**Что нужно сделать:**

1. Создать файл:
   ```
   web/backend/app/api/billing.py
   ```

2. Определить роутер:
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, func
   from typing import Optional
   from datetime import date, datetime
   from decimal import Decimal

   router = APIRouter(prefix="/api/super-admin/billing", tags=["billing"])
   ```

3. Создать endpoint статистики биллинга:
   ```python
   @router.get("/stats")
   async def get_billing_stats(
       start_date: Optional[date] = None,
       end_date: Optional[date] = None,
       company_id: Optional[int] = None,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Получить статистику биллинга"""
       
       # Базовый запрос для суммы
       sum_query = select(
           func.sum(Payment.amount),
           func.count(Payment.id)
       ).where(Payment.status == 'completed')
       
       # Фильтры
       if start_date:
           sum_query = sum_query.where(Payment.payment_date >= start_date)
       if end_date:
           sum_query = sum_query.where(Payment.payment_date <= end_date)
       if company_id:
           sum_query = sum_query.where(Payment.company_id == company_id)
       
       result = await db.execute(sum_query)
       total_amount, count = result.first()
       
       # Выручка по планам
       by_plan_query = select(
           Plan.name,
           func.sum(Payment.amount),
           func.count(Payment.id)
       ).join(Payment.subscription, Subscription.plan, Plan).where(
           Payment.status == 'completed'
       ).group_by(Plan.id, Plan.name)
       
       if start_date:
           by_plan_query = by_plan_query.where(Payment.payment_date >= start_date)
       if end_date:
           by_plan_query = by_plan_query.where(Payment.payment_date <= end_date)
       if company_id:
           by_plan_query = by_plan_query.where(Payment.company_id == company_id)
       
       by_plan_result = await db.execute(by_plan_query)
       by_plan_data = [
           {"plan_name": row[0], "revenue": row[1], "count": row[2]}
           for row in by_plan_result
       ]
       
       return {
           "total_revenue": total_amount or Decimal('0.00'),
           "total_payments": count or 0,
           "by_plan": by_plan_data
       }
   ```

4. Создать endpoint списка платежей:
   ```python
   @router.get("/payments")
   async def get_payments(
       page: int = Query(1, ge=1),
       page_size: int = Query(20, ge=1, le=100),
       company_id: Optional[int] = None,
       status: Optional[str] = None,
       start_date: Optional[date] = None,
       end_date: Optional[date] = None,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Получить список платежей"""
       from sqlalchemy.orm import selectinload
       
       query = select(Payment).options(
           selectinload(Payment.company),
           selectinload(Payment.subscription)
       )
       
       conditions = []
       if company_id:
           conditions.append(Payment.company_id == company_id)
       if status:
           conditions.append(Payment.status == status)
       if start_date:
           conditions.append(Payment.payment_date >= start_date)
       if end_date:
           conditions.append(Payment.payment_date <= end_date)
       
       if conditions:
           query = query.where(and_(*conditions))
       
       # Подсчет общего количества
       count_query = select(func.count(Payment.id))
       if conditions:
           count_query = count_query.where(and_(*conditions))
       
       total = await db.scalar(count_query) or 0
       
       # Пагинация
       query = query.offset((page - 1) * page_size).limit(page_size)
       query = query.order_by(Payment.created_at.desc())
       
       result = await db.execute(query)
       payments = result.scalars().all()
       
       return {
           "items": payments,
           "total": total,
           "page": page,
           "page_size": page_size
       }
   ```

5. Создать endpoint экспорта в Excel:
   ```python
   import pandas as pd
   from fastapi.responses import StreamingResponse
   import io
   
   @router.post("/export")
   async def export_payments(
       start_date: Optional[date] = None,
       end_date: Optional[date] = None,
       company_id: Optional[int] = None,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_super_admin)
   ):
       """Экспорт платежей в Excel"""
       from sqlalchemy.orm import selectinload
       
       # Получаем платежи
       query = select(Payment).options(
           selectinload(Payment.company),
           selectinload(Payment.subscription)
       )
       
       conditions = [Payment.status == 'completed']
       if start_date:
           conditions.append(Payment.payment_date >= start_date)
       if end_date:
           conditions.append(Payment.payment_date <= end_date)
       if company_id:
           conditions.append(Payment.company_id == company_id)
       
       query = query.where(and_(*conditions))
       query = query.order_by(Payment.payment_date.desc())
       
       result = await db.execute(query)
       payments = result.scalars().all()
       
       # Подготавливаем данные для Excel
       data = []
       for payment in payments:
           data.append({
               "ID": payment.id,
               "Компания": payment.company.name if payment.company else "N/A",
               "Сумма": float(payment.amount),
               "Валюта": payment.currency,
               "Дата оплаты": payment.payment_date.strftime('%d.%m.%Y %H:%M') if payment.payment_date else "N/A",
               "Метод оплаты": payment.payment_method,
               "Статус платежа": payment.yookassa_payment_status,
               "Статус": payment.status
           })
       
       # Создаем DataFrame
       df = pd.DataFrame(data)
       
       # Экспортируем в Excel
       output = io.BytesIO()
       with pd.ExcelWriter(output, engine='openpyxl') as writer:
           df.to_excel(writer, index=False, sheet_name='Платежи')
       
       output.seek(0)
       
       filename = f"payments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
       
       return StreamingResponse(
           content=output.read(),
           media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           headers={
               "Content-Disposition": f"attachment; filename={filename}"
           }
       )
   ```

**Критерии выполнения:**
- [ ] Статистика биллинга работает
- [ ] Список платежей работает
- [ ] Фильтры работают
- [ ] Пагинация работает
- [ ] Экспорт в Excel работает
- [ ] Файл скачивается корректно

---

### Подзадача 5.5: Создать get_current_super_admin зависимость

**Описание:** Создать зависимость для проверки прав супер-админа.

**Что нужно сделать:**

1. Создать функцию в dependencies.py:
   ```python
   async def get_current_super_admin(
       db: AsyncSession = Depends(get_db),
       token: str = Depends(oauth2_scheme)
   ) -> SuperAdmin:
       """Получить текущего супер-админа"""
       
       payload = decode_access_token(token)
       telegram_id = payload.get("telegram_id")
       
       if not telegram_id:
           raise HTTPException(
               status_code=401,
               detail="Не удалось определить пользователя"
           )
       
       # Ищем супер-админа
       result = await db.execute(
           select(SuperAdmin).where(SuperAdmin.telegram_id == telegram_id)
       )
       super_admin = result.scalar_one_or_none()
       
       if not super_admin:
           raise HTTPException(
               status_code=403,
               detail="У вас нет прав супер-админа"
           )
       
       return super_admin
   ```

2. Использовать во всех endpoints супер-админа:
   ```python
   @router.get("/dashboard/stats")
   async def get_dashboard_stats(
       current_user: User = Depends(get_current_super_admin),
       db: AsyncSession = Depends(get_db)
   ):
       # ...
   ```

**Критерии выполнения:**
- [ ] Функция создана
- [ ] Проверка прав работает
- [ ] Используется во всех endpoints
- [ ] 403 ошибка возвращается корректно

---

### Подзадача 5.6: Добавить API супер-админа в main.py

**Описание:** Зарегистрировать API модули в главном приложении.

**Что нужно сделать:**

1. Обновить web/backend/main.py:
   ```python
   from app.api.super_admin import router as super_admin_router
   from app.api.billing import router as billing_router
   
   # Регистрируем роутеры
   app.include_router(super_admin_router)
   app.include_router(billing_router)
   ```

**Критерии выполнения:**
- [ ] API модули добавлены
- [ ] Endpoints доступны
- [ ] Swagger документация обновлена
- [ ] Роуты работают

---

## ✅ Чек-лист этапа

### API модули

- [ ] super_admin.py создан
- [ ] billing.py создан
- [ ] Все роутеры определены

### Статистика дашборда

- [ ] Общая статистика работает
- [ ] Выручка считается верно
- [ ] Количество компаний верно
- [ ] Количество платежей верно

### Управление компаниями

- [ ] Список компаний работает
- [ ] Получение компании работает
- [ ] Фильтры работают
- [ ] Пагинация работает
- [ ] Блокировка bookings_only работает
- [ ] Полная блокировка работает
- [ ] Разблокировка работает

### Биллинг

- [ ] Статистика биллинга работает
- [ ] Список платежей работает
- [ ] Фильтры по дате работают
- [ ] Фильтр по компании работает
- [ ] Экспорт в Excel работает

### Авторизация

- [ ] get_current_super_admin создана
- [ ] Проверка прав работает
- [ ] 403 ошибка возвращается

### Интеграция

- [ ] API модули добавлены в main.py
- [ ] Swagger документация обновлена
- [ ] Все endpoints доступны

### Тестирование

- [ ] API протестированы
- [ ] Пагинация проверена
- [ ] Экспорт проверен
- [ ] Нет ошибок в логах

---

## ⚠️ Риски и их решение

### Риск 1: Сложный расчет общей статистики

**Вероятность:** Средняя  
**Влияние:** Низкое

**Меры предупреждения:**
- Упрощение расчетов
- Кеширование результатов
- Периодический пересчет

**Решение при возникновении:**
- Вычисление через cron задачи
- Хранение предрасчитанных значений
- Улучшение запросов

---

### Риск 2: Проблемы с экспортом больших объемов

**Вероятность:** Низкая  
**Влияние:** Среднее

**Меры предупреждения:**
- Ограничение количества записей
- Использование потоков
- Пагинация экспорта

**Решение при возникновении:**
- Разбивка на несколько файлов
- Лимит по времени выполнения
- Фоновое выполнение

---

## 📞 Поддержка

При возникновении проблем:

1. Проверить логи:
   ```bash
   docker compose logs web -f | grep super_admin
   ```

2. Проверить API:
   ```bash
   curl http://localhost:8000/api/super-admin/dashboard/stats
   ```

3. Проверить Swagger:
   ```
   http://localhost:8000/docs
   ```

---

**Этап 5 завершен:** [ ]  
**Дата завершения:** _________  
**Примечания:** _________________

