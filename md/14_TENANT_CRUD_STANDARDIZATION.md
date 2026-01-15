# Этап 3.x: Стандартизация tenant‑CRUD (company_id + tenant session)

**Дата:** 2026-01-14  
**Статус:** 🔄 В процессе  
**Связанный TODO:** `tasks.md` → пункт 4

---

## 🎯 Цель
Сделать единый стандарт работы tenant‑API:
- единый способ определения `company_id`
- единый способ получения tenant‑сессии
- минимизация ручного `SET search_path` в каждом endpoint
- исключение утечек `search_path` через пул соединений

---

## ✅ Принятые решения (MVP)

### 1) Источник `company_id`
Единый порядок:
1. `company_id` из query параметра (если передан)
2. `request.state.company_id` (если выставлен middleware)
3. JWT (`Authorization: Bearer ...`) → claim `company_id`

Если `company_id` не найден — tenant endpoint возвращает **400**.

### 2) Tenant‑сессия
Tenant endpoints получают `AsyncSession` через dependency `get_tenant_db(...)`, который:
- вычисляет `company_id`
- открывает tenant‑сессию через `TenantService.get_tenant_session(company_id)`

### 3) Безопасность search_path
`TenantService.get_tenant_session` обязан:
- установить `search_path` на `"tenant_{company_id}", public`
- **в конце** сбросить `search_path` в `public`, чтобы не было утечки на следующий запрос при переиспользовании соединения из пула

---

## 📦 Что меняем в коде

1. `web/backend/app/deps/tenant.py`
   - `resolve_company_id(request, company_id_query)`
   - `get_tenant_db(request, company_id_query)` → yields tenant `AsyncSession`

2. `web/backend/app/middleware/tenant.py`
   - выставляет `request.state.company_id` из JWT (если есть)

3. Tenant routers:
   - `users_tenant.py`, `clients_tenant.py`, `services_tenant.py`, `masters_tenant.py`, `posts_tenant.py`, частично `bookings.py`
   - убрать дубли `get_company_id_from_token`
   - убрать ручной `SET search_path` и проверки схем, где это покрыто dependency/сервисом

---

## ✅ Критерии готовности
- нет копипасты `get_company_id_from_token` в tenant‑роутерах
- tenant‑роутеры получают `tenant_session` через dependency
- `search_path` не “залипает” между запросами
- `company_id` определяется одинаково во всех tenant endpoints

