# 🔌 API - Документация API Endpoints

Полное описание REST API системы Barber (FastAPI backend).

---

## 📋 Содержание

1. [Общая информация](#общая-информация)
2. [Аутентификация](#аутентификация)
3. [Записи (Bookings)](#записи-bookings)
4. [Услуги (Services)](#услуги-services)
5. [Мастера (Masters)](#мастера-masters)
6. [Рабочие места (Posts)](#рабочие-места-posts)
7. [Клиенты (Clients)](#клиенты-clients)
8. [Календарь (Calendar)](#календарь-calendar)
9. [Слоты времени (Timeslots)](#слоты-времени-timeslots)
10. [Блокировки (Blocks)](#блокировки-blocks)
11. [Статистика (Statistics)](#статистика-statistics)
12. [Экспорт (Export)](#экспорт-export)
13. [Промокоды (Promocodes)](#промокоды-promocodes)
14. [Акции (Promotions)](#акции-promotions)
15. [Рассылки (Broadcasts)](#рассылки-broadcasts)

---

## 🌐 Общая информация

**Base URL:** `http://your-server:8000/api`  
**API Docs:** `http://your-server:8000/docs` (Swagger UI)  
**ReDoc:** `http://your-server:8000/redoc`

### Формат ответов

**Успех:**
```json
{
  "data": { ... },
  "message": "Success",
  "status": "ok"
}
```

**Ошибка:**
```json
{
  "detail": "Error message",
  "status": "error"
}
```

### HTTP статус коды

- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

---

## 🔐 Аутентификация

### POST /api/auth/login

Авторизация в системе (для веб-панели).

**Request:**
```json
{
  "username": "329621295",
  "password": "329621295"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "telegram_id": 329621295,
    "full_name": "Админ Админов",
    "is_admin": true,
    "is_master": false
  }
}
```

---

### POST /api/auth/logout

Выход из системы.

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

### GET /api/auth/me

Получить информацию о текущем пользователе.

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "id": 1,
  "telegram_id": 329621295,
  "username": "admin",
  "full_name": "Админ Админов",
  "is_admin": true,
  "is_master": false
}
```

---

## 📅 Записи (Bookings)

### GET /api/bookings

Получить список записей с фильтрами.

**Query параметры:**
- `page` (int) - номер страницы (default: 1)
- `page_size` (int) - размер страницы (default: 20)
- `status` (string) - фильтр по статусу
- `start_date` (date) - дата начала периода
- `end_date` (date) - дата окончания периода
- `master_id` (int) - фильтр по мастеру
- `service_id` (int) - фильтр по услуге
- `post_id` (int) - фильтр по посту
- `search` (string) - поиск по ФИО, телефону, госномеру

**Example:**
```
GET /api/bookings?page=1&page_size=20&status=confirmed&start_date=2025-12-01&end_date=2025-12-31
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "booking_number": "B-20251227-001",
      "client": {
        "id": 1,
        "full_name": "Петров А.А.",
        "phone": "+79991234567",
        "car_brand": "BMW",
        "car_model": "X5",
        "car_number": "А123BC77"
      },
      "service": {
        "id": 1,
        "name": "ТО",
        "duration": 60,
        "price": 3000
      },
      "master": {
        "id": 1,
        "full_name": "Иван Петров"
      },
      "post": {
        "id": 3,
        "number": 3,
        "name": "Рабочее место №3"
      },
      "date": "2025-12-27",
      "time": "10:00:00",
      "end_time": "11:00:00",
      "duration": 60,
      "status": "confirmed",
      "amount": 3000,
      "is_paid": false,
      "payment_method": null,
      "promocode": null,
      "discount_amount": 0,
      "comment": null,
      "admin_comment": null,
      "created_at": "2025-12-26T15:30:00",
      "confirmed_at": "2025-12-26T15:35:00",
      "completed_at": null,
      "cancelled_at": null
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

---

### GET /api/bookings/{id}

Получить детали конкретной записи.

**Response:**
```json
{
  "id": 1,
  "booking_number": "B-20251227-001",
  "client": { ... },
  "service": { ... },
  "master": { ... },
  "post": { ... },
  "date": "2025-12-27",
  "time": "10:00:00",
  "end_time": "11:00:00",
  "duration": 60,
  "status": "confirmed",
  "amount": 3000,
  "is_paid": false,
  "history": [
    {
      "id": 1,
      "field_name": "status",
      "old_value": "new",
      "new_value": "confirmed",
      "changed_by": "Админ Админов",
      "changed_at": "2025-12-26T15:35:00"
    }
  ]
}
```

---

### POST /api/bookings

Создать новую запись.

**Request:**
```json
{
  "client_id": 1,
  "service_id": 1,
  "date": "2025-12-27",
  "time": "10:00",
  "master_id": null,
  "post_id": null,
  "comment": "Просьба заменить масло",
  "promocode": "SUMMER25"
}
```

**Response:**
```json
{
  "id": 1,
  "booking_number": "B-20251227-001",
  "status": "new",
  "date": "2025-12-27",
  "time": "10:00:00",
  "message": "Запись создана. Ожидайте подтверждения администратора."
}
```

---

### PUT /api/bookings/{id}

Обновить запись.

**Request:**
```json
{
  "master_id": 2,
  "post_id": 5,
  "time": "11:00",
  "comment": "Изменено время"
}
```

**Response:**
```json
{
  "id": 1,
  "message": "Запись обновлена"
}
```

---

### DELETE /api/bookings/{id}

Удалить запись.

**Response:**
```json
{
  "message": "Запись удалена"
}
```

---

### PATCH /api/bookings/{id}/status

Изменить статус записи.

**Request:**
```json
{
  "status": "confirmed",
  "notify_client": true
}
```

**Доступные статусы:**
- `new` - Новая
- `confirmed` - Подтверждена
- `completed` - Выполнена
- `cancelled` - Отменена
- `no_show` - Не явился
- `priority` - Приоритет

**Response:**
```json
{
  "id": 1,
  "status": "confirmed",
  "message": "Статус изменен. Клиент уведомлен."
}
```

---

### PATCH /api/bookings/{id}/master

Назначить/изменить мастера.

**Request:**
```json
{
  "master_id": 2,
  "notify_master": true
}
```

**Response:**
```json
{
  "id": 1,
  "master": {
    "id": 2,
    "full_name": "Петр Сидоров"
  },
  "message": "Мастер назначен. Мастер уведомлен."
}
```

---

### PATCH /api/bookings/{id}/post

Назначить/изменить рабочее место.

**Request:**
```json
{
  "post_id": 5
}
```

**Response:**
```json
{
  "id": 1,
  "post": {
    "id": 5,
    "number": 5
  },
  "message": "Рабочее место назначено"
}
```

---

### PATCH /api/bookings/{id}/payment

Внести сумму и отметить оплату.

**Request:**
```json
{
  "amount": 3000,
  "is_paid": true,
  "payment_method": "cash"
}
```

**Response:**
```json
{
  "id": 1,
  "amount": 3000,
  "is_paid": true,
  "message": "Оплата зафиксирована"
}
```

---

### POST /api/bookings/{id}/notify

Отправить уведомление клиенту.

**Request:**
```json
{
  "message": "Ваша запись подтверждена. Ждем вас 27.12 в 10:00"
}
```

**Response:**
```json
{
  "message": "Уведомление отправлено",
  "sent": true
}
```

---

## 🛠️ Услуги (Services)

### GET /api/services

Получить список услуг.

**Query параметры:**
- `is_active` (boolean) - только активные

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "ТО",
      "description": "Техническое обслуживание",
      "duration": 60,
      "price": 3000,
      "is_active": true,
      "created_at": "2025-01-01T00:00:00"
    }
  ],
  "total": 6
}
```

---

### GET /api/services/{id}

Получить детали услуги.

**Response:**
```json
{
  "id": 1,
  "name": "ТО",
  "description": "Техническое обслуживание",
  "duration": 60,
  "price": 3000,
  "is_active": true,
  "statistics": {
    "total_bookings": 50,
    "total_revenue": 150000,
    "avg_bookings_per_month": 10
  }
}
```

---

### POST /api/services

Создать услугу.

**Request:**
```json
{
  "name": "Полировка кузова",
  "description": "Полировка и защита кузова",
  "duration": 60,
  "price": 5000,
  "is_active": true
}
```

**Response:**
```json
{
  "id": 7,
  "name": "Полировка кузова",
  "message": "Услуга создана"
}
```

---

### PUT /api/services/{id}

Обновить услугу.

### DELETE /api/services/{id}

Удалить услугу.

---

### PATCH /api/services/{id}/toggle

Активировать/деактивировать услугу.

**Request:**
```json
{
  "is_active": false
}
```

---

### GET /api/services/{id}/statistics

Получить статистику по услуге.

**Query параметры:**
- `start_date` (date)
- `end_date` (date)

**Response:**
```json
{
  "service_id": 1,
  "service_name": "ТО",
  "period": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "total_bookings": 50,
  "completed_bookings": 45,
  "cancelled_bookings": 5,
  "total_revenue": 135000,
  "avg_check": 3000,
  "popularity_rank": 1
}
```

---

## 👨‍🔧 Мастера (Masters)

### GET /api/masters

Получить список мастеров.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "full_name": "Иван Петров",
      "telegram_id": 123456789,
      "is_universal": true,
      "specializations": [],
      "statistics": {
        "total_bookings": 100,
        "total_revenue": 300000,
        "avg_load": 75
      }
    }
  ],
  "total": 8
}
```

---

### GET /api/masters/{id}

Детали мастера.

### POST /api/masters

Создать мастера.

**Request:**
```json
{
  "full_name": "Сергей Иванов",
  "telegram_id": 987654321,
  "phone": "+79991234567",
  "is_universal": false,
  "service_ids": [1, 2, 3]
}
```

---

### PUT /api/masters/{id}

Обновить мастера.

### DELETE /api/masters/{id}

Удалить мастера.

---

### GET /api/masters/{id}/statistics

Статистика мастера.

**Query параметры:**
- `start_date`, `end_date`

**Response:**
```json
{
  "master_id": 1,
  "master_name": "Иван Петров",
  "period": { ... },
  "total_bookings": 50,
  "completed_bookings": 48,
  "total_revenue": 150000,
  "avg_check": 3125,
  "load_percentage": 85,
  "top_services": [
    { "service_name": "ТО", "count": 30 },
    { "service_name": "Диагностика", "count": 15 }
  ]
}
```

---

### GET /api/masters/{id}/schedule

Расписание мастера на дату.

**Query параметры:**
- `date` (date, required)

**Response:**
```json
{
  "master_id": 1,
  "master_name": "Иван Петров",
  "date": "2025-12-27",
  "bookings": [
    {
      "id": 1,
      "time": "09:00",
      "end_time": "10:00",
      "client_name": "Петров А.А.",
      "service_name": "ТО",
      "post_number": 3,
      "status": "confirmed"
    }
  ]
}
```

---

## 🏢 Посты (Posts)

### GET /api/posts

Список постов.

### GET /api/posts/{id}

Детали поста.

### POST /api/posts

Создать пост.

### PUT /api/posts/{id}

Обновить пост.

### DELETE /api/posts/{id}

Удалить пост.

---

### GET /api/posts/{id}/statistics

Статистика поста.

**Response:**
```json
{
  "post_id": 3,
  "post_number": 3,
  "period": { ... },
  "total_bookings": 80,
  "load_percentage": 70,
  "total_revenue": 240000,
  "top_services": [ ... ]
}
```

---

### GET /api/posts/{id}/schedule

Расписание поста на дату.

---

## 👥 Клиенты (Clients)

### GET /api/clients

Список клиентов.

**Query параметры:**
- `page`, `page_size`
- `search` (string) - по ФИО, телефону, госномеру

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "full_name": "Петров А.А.",
      "phone": "+79991234567",
      "car_brand": "BMW",
      "car_model": "X5",
      "car_number": "А123BC77",
      "total_visits": 15,
      "total_amount": 45000,
      "last_visit": "2025-12-20"
    }
  ],
  "total": 200,
  "page": 1,
  "pages": 10
}
```

---

### GET /api/clients/{id}

Детали клиента.

---

### GET /api/clients/{id}/bookings

Список записей клиента.

---

### GET /api/clients/{id}/history

История обслуживания клиента.

**Response:**
```json
{
  "client_id": 1,
  "client_name": "Петров А.А.",
  "car": "BMW X5 (А123BC77)",
  "history": [
    {
      "date": "2025-12-20",
      "service_name": "ТО",
      "master_name": "Иван Петров",
      "amount": 3000,
      "notes": null
    }
  ],
  "total_visits": 15,
  "total_amount": 45000
}
```

---

### GET /api/clients/{id}/statistics

Статистика клиента.

---

## 📅 Календарь (Calendar)

### GET /api/calendar

Получить календарь записей.

**Query параметры:**
- `start_date` (date, required)
- `end_date` (date, required)
- `view` (string) - month, week, day
- `master_id` (int) - фильтр по мастеру
- `post_id` (int) - фильтр по посту
- `service_id` (int) - фильтр по услуге
- `status` (string) - фильтр по статусу

**Example:**
```
GET /api/calendar?start_date=2025-12-01&end_date=2025-12-31&view=month
```

**Response:**
```json
{
  "start_date": "2025-12-01",
  "end_date": "2025-12-31",
  "view": "month",
  "dates": [
    {
      "date": "2025-12-27",
      "day_of_week": "Friday",
      "bookings_count": 8,
      "bookings": [
        {
          "id": 1,
          "time": "10:00",
          "end_time": "11:00",
          "client_name": "Петров А.А.",
          "service_name": "ТО",
          "master_name": "Иван Петров",
          "post_number": 3,
          "status": "confirmed",
          "color": "#4caf50"
        }
      ]
    }
  ]
}
```

---

## ⏰ Слоты времени (Timeslots)

### GET /api/timeslots/available

Получить доступные слоты на дату.

**Query параметры:**
- `date` (date, required)
- `service_id` (int, required) - для определения длительности
- `duration` (int) - длительность в минутах (опционально, берется из service)
- `master_id` (int) - конкретный мастер (опционально)

**Example:**
```
GET /api/timeslots/available?date=2025-12-27&service_id=1
```

**Response:**
```json
{
  "date": "2025-12-27",
  "service_id": 1,
  "duration": 60,
  "slots": [
    {
      "time": "09:00",
      "end_time": "10:00",
      "available_masters": [1, 2, 3],
      "available_posts": [1, 2, 3, 4, 5],
      "is_available": true
    },
    {
      "time": "09:30",
      "end_time": "10:30",
      "available_masters": [1, 3],
      "available_posts": [2, 4, 5],
      "is_available": true
    },
    {
      "time": "10:00",
      "end_time": "11:00",
      "available_masters": [],
      "available_posts": [],
      "is_available": false
    }
  ]
}
```

---

## 🚫 Блокировки (Blocks)

### GET /api/blocks

Список блокировок.

**Query параметры:**
- `start_date`, `end_date`
- `block_type` (string) - full_service, master, post, service

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "block_type": "full_service",
      "start_date": "2025-12-31",
      "end_date": "2026-01-01",
      "start_time": null,
      "end_time": null,
      "reason": null,
      "created_at": "2025-12-20T10:00:00"
    },
    {
      "id": 2,
      "block_type": "master",
      "master": {
        "id": 1,
        "full_name": "Иван Петров"
      },
      "start_date": "2026-01-15",
      "end_date": "2026-01-20",
      "start_time": null,
      "end_time": null,
      "reason": "Отпуск"
    }
  ]
}
```

---

### POST /api/blocks

Создать блокировку.

**Request:**
```json
{
  "block_type": "master",
  "master_id": 1,
  "start_date": "2026-01-15",
  "end_date": "2026-01-20",
  "start_time": null,
  "end_time": null,
  "reason": "Отпуск"
}
```

**Типы блокировок:**
- `full_service` - весь салон красоты
- `master` - конкретный мастер (укажите `master_id`)
- `post` - конкретное рабочее место (укажите `post_id`)
- `service` - конкретная услуга (укажите `service_id`)

**Response:**
```json
{
  "id": 2,
  "message": "Блокировка создана"
}
```

---

### DELETE /api/blocks/{id}

Удалить блокировку.

---

### PATCH /api/blocks/toggle-accepting

Глобальная кнопка приема заявок.

**Request:**
```json
{
  "accepting": false
}
```

**Response:**
```json
{
  "accepting": false,
  "message": "Прием заявок ОТКЛЮЧЕН"
}
```

---

## 📊 Статистика (Statistics)

### GET /api/statistics/overview

Общая статистика.

**Query параметры:**
- `start_date`, `end_date`

**Response:**
```json
{
  "period": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "bookings_count": 150,
  "bookings_confirmed": 140,
  "bookings_completed": 120,
  "bookings_cancelled": 10,
  "bookings_no_show": 5,
  "revenue": 450000,
  "avg_check": 3000,
  "no_show_percent": 3.3,
  "conversion": 93.3,
  "new_clients": 30,
  "returning_clients": 120
}
```

---

### GET /api/statistics/by-masters

Статистика по мастерам.

**Response:**
```json
{
  "period": { ... },
  "masters": [
    {
      "master_id": 1,
      "master_name": "Иван Петров",
      "bookings_count": 50,
      "revenue": 150000,
      "load_percentage": 85,
      "avg_check": 3000
    }
  ]
}
```

---

### GET /api/statistics/by-services

Статистика по услугам.

---

### GET /api/statistics/by-posts

Статистика по постам.

---

### GET /api/statistics/by-time

Почасовая статистика (пики загрузки).

**Response:**
```json
{
  "period": { ... },
  "hourly_stats": [
    { "hour": 9, "bookings_count": 20, "load_percentage": 90 },
    { "hour": 10, "bookings_count": 22, "load_percentage": 100 },
    { "hour": 11, "bookings_count": 18, "load_percentage": 75 }
  ]
}
```

---

### GET /api/statistics/by-clients

Статистика по клиентам.

---

### GET /api/statistics/daily

Ежедневная статистика.

**Response:**
```json
{
  "period": { ... },
  "daily_stats": [
    {
      "date": "2025-12-01",
      "bookings": 5,
      "revenue": 15000,
      "no_shows": 0,
      "load_percentage": 60
    }
  ]
}
```

---

## 📤 Экспорт (Export)

### GET /api/export/bookings

Экспорт записей в Excel.

**Query параметры:**
- `format` (string) - xlsx (default)
- `start_date`, `end_date`
- `status` (string)

**Response:** Excel файл

---

### GET /api/export/clients

Экспорт клиентов в Excel.

---

### GET /api/export/statistics

Экспорт статистики в Excel.

---

### GET /api/export/work-orders

Экспорт лист-нарядов в Excel.

**Query параметры:**
- `date` (date, required)
- `master_id` (int, optional)

---

## 🎟️ Промокоды (Promocodes)

### GET /api/promocodes

Список промокодов.

---

### POST /api/promocodes

Создать промокод.

**Request:**
```json
{
  "code": "SUMMER25",
  "discount_type": "percent",
  "discount_value": 15,
  "service_id": 1,
  "min_amount": 2000,
  "max_uses": 100,
  "start_date": "2025-06-01",
  "end_date": "2025-08-31",
  "description": "Летняя акция на ТО"
}
```

---

### GET /api/promocodes/validate/{code}

Валидировать промокод.

**Query параметры:**
- `service_id` (int)
- `amount` (float)

**Response:**
```json
{
  "valid": true,
  "promocode": {
    "id": 1,
    "code": "SUMMER25",
    "discount_type": "percent",
    "discount_value": 15
  },
  "discount_amount": 450,
  "final_amount": 2550
}
```

---

### GET /api/promocodes/{id}/statistics

Статистика промокода.

---

## 🎉 Акции (Promotions)

### GET /api/promotions

Список акций.

---

### POST /api/promotions

Создать акцию.

---

### GET /api/promotions/active

Активные акции.

**Query параметры:**
- `service_id` (int, optional)

---

## 📢 Рассылки (Broadcasts)

### GET /api/broadcasts

Список рассылок.

---

### POST /api/broadcasts

Создать рассылку.

**Request:**
```json
{
  "text": "Новогодняя акция! Скидка 20%",
  "image_path": null,
  "target_audience": "active",
  "filter_params": {
    "months": 3
  }
}
```

**Целевые аудитории:**
- `all` - все клиенты
- `active` - активные (filter_params.months)
- `new` - новые (filter_params.days)
- `by_service` - по услуге (filter_params.service_id)

**Response:**
```json
{
  "id": 1,
  "status": "sending",
  "message": "Рассылка запущена"
}
```

---

### GET /api/broadcasts/{id}

Детали рассылки.

---

### DELETE /api/broadcasts/{id}

Удалить рассылку.

---

## 📝 Примеры использования

### Создание записи с промокодом

```javascript
// 1. Валидация промокода
const validateResponse = await fetch(
  '/api/promocodes/validate/SUMMER25?service_id=1&amount=3000'
);
const validation = await validateResponse.json();
// { valid: true, discount_amount: 450, final_amount: 2550 }

// 2. Получение доступных слотов
const slotsResponse = await fetch(
  '/api/timeslots/available?date=2025-12-27&service_id=1'
);
const slots = await slotsResponse.json();
// { slots: [{ time: "09:00", is_available: true }, ...] }

// 3. Создание записи
const bookingResponse = await fetch('/api/bookings', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_id: 1,
    service_id: 1,
    date: '2025-12-27',
    time: '09:00',
    promocode: 'SUMMER25'
  })
});
const booking = await bookingResponse.json();
// { id: 1, booking_number: "B-20251227-001", status: "new" }
```

### Работа с календарем

```javascript
// Получение календаря на месяц
const response = await fetch(
  '/api/calendar?start_date=2025-12-01&end_date=2025-12-31&view=month',
  {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  }
);
const calendar = await response.json();
// { dates: [{ date: "2025-12-27", bookings: [...] }] }
```

### Статистика за период

```javascript
// Общая статистика
const statsResponse = await fetch(
  '/api/statistics/overview?start_date=2025-12-01&end_date=2025-12-31',
  {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  }
);
const stats = await statsResponse.json();
// { bookings_count: 150, revenue: 450000, ... }
```

---

## 🔒 Безопасность

### Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Rate Limiting

API защищен от злоупотреблений:
- **Общие endpoints:** 100 запросов/минуту
- **Auth endpoints:** 10 запросов/минуту
- **Export endpoints:** 5 запросов/минуту

### CORS

Разрешенные origins настраиваются через `WEB_CORS_ORIGINS` в `.env`.

---

## 📚 Дополнительные ресурсы

- **Swagger UI:** `/docs` - интерактивная документация
- **ReDoc:** `/redoc` - альтернативная документация
- **OpenAPI Schema:** `/openapi.json` - схема в формате OpenAPI 3.0

---

**Версия API:** 1.0.0  
**Последнее обновление:** 27 декабря 2025