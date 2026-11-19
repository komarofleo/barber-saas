#!/usr/bin/env python3
"""Залить демо-данные на ноябрь 2026 в tenant_1 (тестовая организация).

Использование на сервере:
  docker exec -i barber_postgres psql -U barber_user -d barber_db < <(python3 -c "from seed_november_demo_tenant1 import SQL; print(SQL)")
или:
  python3 web/backend/scripts/seed_november_demo_tenant1.py | \
    docker exec -i -e PGPASSWORD=$DB_PASSWORD barber_postgres psql -U barber_user -d barber_db -v ON_ERROR_STOP=1
"""

from __future__ import annotations

SQL = r"""-- Демо-данные на ноябрь 2026 для тестовой организации (tenant_1)
-- Безопасно перезапускать: чистит только ранее залитые demo-записи (booking_number LIKE 'DEMO-NOV-%'
-- и клиентов/юзеров с telegram_id 910000001..910000020).

SET search_path TO tenant_1, public;

BEGIN;

-- ---------------------------------------------------------------------------
-- Очистка предыдущего демо-сида
-- ---------------------------------------------------------------------------
DELETE FROM client_history
WHERE booking_id IN (SELECT id FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%');

DELETE FROM booking_history
WHERE booking_id IN (SELECT id FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%');

DELETE FROM notifications
WHERE booking_id IN (SELECT id FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%')
   OR user_id IN (SELECT id FROM users WHERE telegram_id BETWEEN 910000001 AND 910000030);

DELETE FROM timeslots
WHERE booking_id IN (SELECT id FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%');

DELETE FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%';

DELETE FROM clients
WHERE user_id IN (SELECT id FROM users WHERE telegram_id BETWEEN 910000001 AND 910000020);

DELETE FROM master_services
WHERE master_id IN (
  SELECT id FROM masters WHERE telegram_id BETWEEN 910000021 AND 910000023
);

DELETE FROM masters WHERE telegram_id BETWEEN 910000021 AND 910000023;

DELETE FROM users WHERE telegram_id BETWEEN 910000001 AND 910000030;

DELETE FROM promocodes WHERE code LIKE 'DEMO%';
DELETE FROM promotions WHERE name LIKE 'Демо %';
DELETE FROM blocked_slots WHERE reason LIKE 'Демо:%';
DELETE FROM broadcasts WHERE text LIKE 'Демо:%';

DELETE FROM services WHERE name IN (
  'Укладка', 'Маникюр классический', 'Комплекс барбер'
);

-- ---------------------------------------------------------------------------
-- Доп. услуги
-- ---------------------------------------------------------------------------
INSERT INTO services (name, description, duration, price, is_active, created_at, updated_at)
VALUES
  ('Укладка', 'Укладка волос феном / стайлинг', 40, 1200.00, true, NOW(), NOW()),
  ('Маникюр классический', 'Классический маникюр без покрытия', 60, 1800.00, true, NOW(), NOW()),
  ('Комплекс барбер', 'Стрижка + борода + уход', 70, 1800.00, true, NOW(), NOW());

-- ---------------------------------------------------------------------------
-- Пользователи-клиенты (10)
-- ---------------------------------------------------------------------------
INSERT INTO users (
  telegram_id, username, first_name, last_name, phone,
  is_admin, is_master, is_blocked, created_at, updated_at
) VALUES
  (910000001, 'anna_ivanova',   'Анна',     'Иванова',   '+79990010001', false, false, false, NOW(), NOW()),
  (910000002, 'petr_smirnov',   'Пётр',     'Смирнов',   '+79990010002', false, false, false, NOW(), NOW()),
  (910000003, 'olga_kozlova',   'Ольга',    'Козлова',   '+79990010003', false, false, false, NOW(), NOW()),
  (910000004, 'dmitry_volkov',  'Дмитрий',  'Волков',    '+79990010004', false, false, false, NOW(), NOW()),
  (910000005, 'elena_novikova', 'Елена',    'Новикова',  '+79990010005', false, false, false, NOW(), NOW()),
  (910000006, 'sergey_morozov', 'Сергей',   'Морозов',   '+79990010006', false, false, false, NOW(), NOW()),
  (910000007, 'natalia_lebed',  'Наталья',  'Лебедева',  '+79990010007', false, false, false, NOW(), NOW()),
  (910000008, 'igor_sokolov',   'Игорь',    'Соколов',   '+79990010008', false, false, false, NOW(), NOW()),
  (910000009, 'maria_orlova',   'Мария',    'Орлова',    '+79990010009', false, false, false, NOW(), NOW()),
  (910000010, 'alex_fedorov',   'Алексей',  'Фёдоров',   '+79990010010', false, false, false, NOW(), NOW());

-- Пользователи-мастера (для связи с masters)
INSERT INTO users (
  telegram_id, username, first_name, last_name, phone,
  is_admin, is_master, is_blocked, created_at, updated_at
) VALUES
  (910000021, 'ivan_barber',  'Иван',  'Петров',   '+79991111111', false, true, false, NOW(), NOW()),
  (910000022, 'maria_hair',   'Мария', 'Сидорова', '+79992222222', false, true, false, NOW(), NOW()),
  (910000023, 'kate_nails',   'Екатерина', 'Белова', '+79993333333', false, true, false, NOW(), NOW());

-- Привязка существующих мастеров к пользователям
UPDATE masters m
SET user_id = u.id,
    telegram_id = u.telegram_id,
    phone = COALESCE(m.phone, u.phone),
    updated_at = NOW()
FROM users u
WHERE m.full_name = 'Иван Петров' AND u.telegram_id = 910000021;

UPDATE masters m
SET user_id = u.id,
    telegram_id = u.telegram_id,
    phone = COALESCE(m.phone, u.phone),
    updated_at = NOW()
FROM users u
WHERE m.full_name = 'Мария Сидорова' AND u.telegram_id = 910000022;

-- Третий мастер
INSERT INTO masters (
  user_id, full_name, phone, telegram_id, specialization, is_universal, created_at, updated_at
)
SELECT id, 'Екатерина Белова', phone, telegram_id, 'Маникюр', false, NOW(), NOW()
FROM users WHERE telegram_id = 910000023;

-- Клиенты
INSERT INTO clients (user_id, full_name, phone, total_visits, total_amount, created_at, updated_at)
SELECT
  u.id,
  u.first_name || ' ' || u.last_name,
  u.phone,
  0,
  0.00,
  NOW(),
  NOW()
FROM users u
WHERE u.telegram_id BETWEEN 910000001 AND 910000010;

-- Рабочее место 3
INSERT INTO posts (number, name, description, is_active, created_at, updated_at)
VALUES (3, 'Место 3', 'Маникюрный стол', true, NOW(), NOW())
ON CONFLICT (number) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, is_active = true;

-- ---------------------------------------------------------------------------
-- Связи мастер ↔ услуга
-- ---------------------------------------------------------------------------
INSERT INTO master_services (master_id, service_id, created_at)
SELECT m.id, s.id, NOW()
FROM masters m
CROSS JOIN services s
WHERE m.full_name = 'Иван Петров'
  AND s.name IN ('Стрижка мужская', 'Борода', 'Комплекс барбер')
  AND NOT EXISTS (
    SELECT 1 FROM master_services ms WHERE ms.master_id = m.id AND ms.service_id = s.id
  );

INSERT INTO master_services (master_id, service_id, created_at)
SELECT m.id, s.id, NOW()
FROM masters m
CROSS JOIN services s
WHERE m.full_name = 'Мария Сидорова'
  AND s.name IN ('Стрижка женская', 'Окрашивание', 'Укладка')
  AND NOT EXISTS (
    SELECT 1 FROM master_services ms WHERE ms.master_id = m.id AND ms.service_id = s.id
  );

INSERT INTO master_services (master_id, service_id, created_at)
SELECT m.id, s.id, NOW()
FROM masters m
CROSS JOIN services s
WHERE m.full_name = 'Екатерина Белова'
  AND s.name IN ('Маникюр классический')
  AND NOT EXISTS (
    SELECT 1 FROM master_services ms WHERE ms.master_id = m.id AND ms.service_id = s.id
  );

-- ---------------------------------------------------------------------------
-- Промокоды и акции на ноябрь
-- ---------------------------------------------------------------------------
INSERT INTO promocodes (
  code, discount_type, discount_value, service_id, min_amount, max_uses, current_uses,
  start_date, end_date, is_active, description, created_at, updated_at
) VALUES
  ('DEMO10', 'percent', 10.00, NULL, 0.00, 100, 12,
   '2026-11-01', '2026-11-30', true, 'Демо: −10% на любую услугу', NOW(), NOW()),
  ('DEMOFIX300', 'fixed', 300.00, (SELECT id FROM services WHERE name = 'Окрашивание' LIMIT 1), 2000.00, 50, 3,
   '2026-11-01', '2026-11-30', true, 'Демо: −300 ₽ на окрашивание', NOW(), NOW()),
  ('DEMOEXPIRED', 'percent', 20.00, NULL, 0.00, 10, 10,
   '2026-10-01', '2026-10-31', false, 'Демо: истёкший промокод', NOW(), NOW());

INSERT INTO promotions (
  name, description, discount_type, discount_value, service_id,
  start_date, end_date, is_active, created_at, updated_at
) VALUES
  ('Демо Ноябрь: стрижка', 'Скидка на мужскую стрижку всю неделю', 'percent', 15.00,
   (SELECT id FROM services WHERE name = 'Стрижка мужская' LIMIT 1),
   '2026-11-01', '2026-11-30', true, NOW(), NOW()),
  ('Демо Окрашивание −500', 'Фикс-скидка на окрашивание', 'fixed', 500.00,
   (SELECT id FROM services WHERE name = 'Окрашивание' LIMIT 1),
   '2026-11-10', '2026-11-25', true, NOW(), NOW());

-- ---------------------------------------------------------------------------
-- Блокировки
-- ---------------------------------------------------------------------------
INSERT INTO blocked_slots (
  block_type, master_id, post_id, service_id,
  start_date, end_date, start_time, end_time, reason, created_by, created_at
) VALUES
  (
    'master',
    (SELECT id FROM masters WHERE full_name = 'Иван Петров' LIMIT 1),
    NULL, NULL,
    '2026-11-23', '2026-11-23', '13:00', '15:00',
    'Демо: обеденный перерыв мастера',
    (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
    NOW()
  ),
  (
    'post',
    NULL,
    (SELECT id FROM posts WHERE number = 3 LIMIT 1),
    NULL,
    '2026-11-20', '2026-11-20', '10:00', '12:00',
    'Демо: обслуживание маникюрного стола',
    (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
    NOW()
  ),
  (
    'full_service',
    NULL, NULL, NULL,
    '2026-11-04', '2026-11-04', NULL, NULL,
    'Демо: санитарный день',
    (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
    NOW()
  );

-- ---------------------------------------------------------------------------
-- Настройки салона
-- ---------------------------------------------------------------------------
INSERT INTO settings (key, value, description, updated_at) VALUES
  ('work_start_time', '09:00', 'Начало рабочего дня', NOW()),
  ('work_end_time', '20:00', 'Конец рабочего дня', NOW()),
  ('slot_duration', '30', 'Длительность слота (мин)', NOW()),
  ('reminder_day_enabled', 'true', 'Напоминание за сутки', NOW()),
  ('reminder_hour_enabled', 'true', 'Напоминание за час', NOW()),
  ('salon_name', 'Тестовый салон красоты', 'Название салона', NOW()),
  ('timezone', 'Europe/Moscow', 'Часовой пояс', NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

-- ---------------------------------------------------------------------------
-- Рассылки
-- ---------------------------------------------------------------------------
INSERT INTO broadcasts (
  text, image_path, target_audience, filter_params, status,
  total_sent, total_errors, created_by, created_at, sent_at
) VALUES
  (
    'Демо: Добро пожаловать в ноябрь! Скидка 10% по коду DEMO10.',
    NULL, 'all', NULL, 'completed', 10, 0,
    (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
    '2026-11-01 10:00:00', '2026-11-01 10:05:00'
  ),
  (
    'Демо: Напоминание о записи завтра — не забудьте!',
    NULL, 'active', NULL, 'pending', 0, 0,
    (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
    NOW(), NULL
  );

-- ---------------------------------------------------------------------------
-- Записи на ноябрь 2026
-- Вспомогательные CTE с клиентами / услугами / мастерами / постами
-- ---------------------------------------------------------------------------
WITH
c AS (
  SELECT full_name, id,
         ROW_NUMBER() OVER (ORDER BY id) AS rn
  FROM clients
  WHERE user_id IN (SELECT id FROM users WHERE telegram_id BETWEEN 910000001 AND 910000010)
),
s AS (
  SELECT name, id, duration, price FROM services
),
m AS (
  SELECT full_name, id FROM masters
),
p AS (
  SELECT number, id FROM posts
),
admin AS (
  SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1
),
promo AS (
  SELECT id FROM promocodes WHERE code = 'DEMO10' LIMIT 1
),
seed(day, hh, mm, client_rn, service_name, master_name, post_num, status, paid, pay_method, comment, use_promo) AS (
  VALUES
  -- Прошлая часть ноября (1–18): completed / cancelled / no_show
  ('2026-11-01'::date, 10, 0,  1, 'Стрижка мужская',      'Иван Петров',      1, 'completed', true,  'cash', 'Демо: утренняя стрижка', false),
  ('2026-11-01',       12, 0,  2, 'Стрижка женская',      'Мария Сидорова',   2, 'completed', true,  'card', NULL, false),
  ('2026-11-02',       11, 0,  3, 'Борода',               'Иван Петров',      1, 'completed', true,  'qr',   NULL, false),
  ('2026-11-03',       15, 0,  4, 'Окрашивание',          'Мария Сидорова',   2, 'cancelled', false, NULL,  'Клиент отменил', false),
  ('2026-11-05',        9,30,  5, 'Маникюр классический', 'Екатерина Белова', 3, 'completed', true,  'card', NULL, false),
  ('2026-11-05',       14, 0,  6, 'Комплекс барбер',      'Иван Петров',      1, 'completed', true,  'cash', NULL, true),
  ('2026-11-06',       10, 0,  7, 'Укладка',              'Мария Сидорова',   2, 'no_show',   false, NULL,  'Не пришёл', false),
  ('2026-11-07',       16, 0,  8, 'Стрижка мужская',      'Иван Петров',      1, 'completed', true,  'card', NULL, false),
  ('2026-11-08',       11,30,  9, 'Стрижка женская',      'Мария Сидорова',   2, 'completed', true,  'qr',   NULL, false),
  ('2026-11-09',       13, 0, 10, 'Маникюр классический', 'Екатерина Белова', 3, 'completed', true,  'cash', NULL, false),
  ('2026-11-10',       10, 0,  1, 'Окрашивание',          'Мария Сидорова',   2, 'completed', true,  'card', 'Демо с промо', true),
  ('2026-11-11',       12, 0,  2, 'Борода',               'Иван Петров',      1, 'completed', true,  'cash', NULL, false),
  ('2026-11-12',       15,30,  3, 'Стрижка женская',      'Мария Сидорова',   2, 'cancelled', false, NULL,  NULL, false),
  ('2026-11-13',        9, 0,  4, 'Стрижка мужская',      'Иван Петров',      1, 'completed', true,  'qr',   NULL, false),
  ('2026-11-14',       17, 0,  5, 'Укладка',              'Мария Сидорова',   2, 'completed', true,  'card', NULL, false),
  ('2026-11-15',       11, 0,  6, 'Комплекс барбер',      'Иван Петров',      1, 'completed', true,  'cash', NULL, false),
  ('2026-11-16',       13,30,  7, 'Маникюр классический', 'Екатерина Белова', 3, 'completed', true,  'card', NULL, false),
  ('2026-11-17',       10, 0,  8, 'Стрижка мужская',      'Иван Петров',      1, 'completed', false, NULL,  'Оплата на месте не прошла', false),
  ('2026-11-18',       12, 0,  9, 'Стрижка женская',      'Мария Сидорова',   2, 'completed', true,  'cash', NULL, false),
  ('2026-11-18',       16, 0, 10, 'Борода',               'Иван Петров',      1, 'no_show',   false, NULL,  NULL, false),

  -- Сегодня 19.11 — микс статусов для дашборда
  ('2026-11-19',        9, 0,  1, 'Стрижка мужская',      'Иван Петров',      1, 'completed', true,  'cash', 'Утро', false),
  ('2026-11-19',       10,30,  2, 'Маникюр классический', 'Екатерина Белова', 3, 'completed', true,  'card', NULL, false),
  ('2026-11-19',       12, 0,  3, 'Укладка',              'Мария Сидорова',   2, 'confirmed', false, NULL,  'После обеда', false),
  ('2026-11-19',       14, 0,  4, 'Комплекс барбер',      'Иван Петров',      1, 'confirmed', false, NULL,  NULL, true),
  ('2026-11-19',       15,30,  5, 'Стрижка женская',      'Мария Сидорова',   2, 'new',       false, NULL,  'Новая заявка', false),
  ('2026-11-19',       17, 0,  6, 'Борода',               'Иван Петров',      1, 'new',       false, NULL,  NULL, false),
  ('2026-11-19',       18, 0,  7, 'Окрашивание',          'Мария Сидорова',   2, 'priority',  false, NULL,  'Приоритет VIP', false),

  -- Ближайшие дни
  ('2026-11-20',       10, 0,  8, 'Стрижка мужская',      'Иван Петров',      1, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-20',       11,30,  9, 'Маникюр классический', 'Екатерина Белова', 3, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-20',       15, 0, 10, 'Стрижка женская',      'Мария Сидорова',   2, 'new',       false, NULL,  NULL, false),
  ('2026-11-21',       12, 0,  1, 'Окрашивание',          'Мария Сидорова',   2, 'confirmed', false, NULL,  NULL, true),
  ('2026-11-21',       16, 0,  2, 'Комплекс барбер',      'Иван Петров',      1, 'new',       false, NULL,  NULL, false),
  ('2026-11-22',       10, 0,  3, 'Укладка',              'Мария Сидорова',   2, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-22',       13, 0,  4, 'Борода',               'Иван Петров',      1, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-24',       11, 0,  5, 'Стрижка мужская',      'Иван Петров',      1, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-24',       14,30,  6, 'Маникюр классический', 'Екатерина Белова', 3, 'new',       false, NULL,  NULL, false),
  ('2026-11-25',       10, 0,  7, 'Стрижка женская',      'Мария Сидорова',   2, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-25',       17, 0,  8, 'Окрашивание',          'Мария Сидорова',   2, 'priority',  false, NULL,  'Свадьба', false),
  ('2026-11-26',        9,30,  9, 'Комплекс барбер',      'Иван Петров',      1, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-27',       12, 0, 10, 'Укладка',              'Мария Сидорова',   2, 'new',       false, NULL,  NULL, false),
  ('2026-11-28',       15, 0,  1, 'Стрижка мужская',      'Иван Петров',      1, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-29',       11, 0,  2, 'Маникюр классический', 'Екатерина Белова', 3, 'confirmed', false, NULL,  NULL, false),
  ('2026-11-30',       16, 0,  3, 'Стрижка женская',      'Мария Сидорова',   2, 'new',       false, NULL,  NULL, false)
)
INSERT INTO bookings (
  booking_number, client_id, service_id, master_id, post_id, created_by,
  service_date, request_date, time, duration, end_time, status,
  amount, is_paid, payment_method, promocode_id, discount_amount,
  comment, admin_comment, created_at, updated_at,
  confirmed_at, completed_at, cancelled_at
)
SELECT
  'DEMO-NOV-' || to_char(seed.day, 'DD') || '-' || lpad(seed.hh::text, 2, '0') || lpad(seed.mm::text, 2, '0') || '-' || seed.client_rn,
  c.id,
  s.id,
  m.id,
  p.id,
  (SELECT id FROM admin),
  seed.day,
  seed.day - 1,
  make_time(seed.hh, seed.mm, 0),
  s.duration,
  (make_time(seed.hh, seed.mm, 0) + (s.duration || ' minutes')::interval)::time,
  seed.status,
  CASE
    WHEN seed.use_promo THEN ROUND(s.price * 0.90, 2)
    ELSE s.price
  END,
  seed.paid,
  seed.pay_method,
  CASE WHEN seed.use_promo THEN (SELECT id FROM promo) ELSE NULL END,
  CASE WHEN seed.use_promo THEN ROUND(s.price * 0.10, 2) ELSE 0.00 END,
  seed.comment,
  CASE WHEN seed.status = 'priority' THEN 'VIP' ELSE NULL END,
  seed.day::timestamp + make_time(GREATEST(seed.hh - 2, 8), 0, 0),
  NOW(),
  CASE WHEN seed.status IN ('confirmed', 'completed', 'priority') THEN seed.day::timestamp + make_time(seed.hh, seed.mm, 0) - interval '1 day' ELSE NULL END,
  CASE WHEN seed.status = 'completed' THEN seed.day::timestamp + make_time(seed.hh, seed.mm, 0) + (s.duration || ' minutes')::interval ELSE NULL END,
  CASE WHEN seed.status IN ('cancelled', 'no_show') THEN seed.day::timestamp + make_time(seed.hh, seed.mm, 0) ELSE NULL END
FROM seed
JOIN c ON c.rn = seed.client_rn
JOIN s ON s.name = seed.service_name
JOIN m ON m.full_name = seed.master_name
JOIN p ON p.number = seed.post_num;

-- История клиентов по completed
INSERT INTO client_history (client_id, booking_id, service_id, master_id, date, amount, notes, created_at)
SELECT
  b.client_id, b.id, b.service_id, b.master_id, b.service_date, b.amount,
  'Демо визит', b.completed_at
FROM bookings b
WHERE b.booking_number LIKE 'DEMO-NOV-%' AND b.status = 'completed';

-- Обновить агрегаты клиентов
UPDATE clients cl
SET
  total_visits = sub.visits,
  total_amount = sub.amount,
  updated_at = NOW()
FROM (
  SELECT client_id, COUNT(*) AS visits, COALESCE(SUM(amount), 0) AS amount
  FROM bookings
  WHERE booking_number LIKE 'DEMO-NOV-%' AND status = 'completed'
  GROUP BY client_id
) sub
WHERE cl.id = sub.client_id;

-- История статусов (пара записей)
INSERT INTO booking_history (booking_id, changed_by, field_name, old_value, new_value, changed_at)
SELECT
  b.id,
  (SELECT id FROM users WHERE is_admin = true ORDER BY id LIMIT 1),
  'status',
  'new',
  b.status,
  COALESCE(b.confirmed_at, b.completed_at, b.cancelled_at, b.created_at)
FROM bookings b
WHERE b.booking_number LIKE 'DEMO-NOV-%'
  AND b.status IN ('confirmed', 'completed', 'cancelled', 'priority');

-- Уведомления
INSERT INTO notifications (
  user_id, booking_id, notification_type, message, is_sent, sent_at, created_at
)
SELECT
  cl.user_id,
  b.id,
  CASE
    WHEN b.status = 'confirmed' THEN 'reminder_day'
    WHEN b.status = 'completed' THEN 'status_change'
    ELSE 'reminder_hour'
  END,
  'Демо: уведомление по записи ' || b.booking_number,
  true,
  NOW() - interval '2 hours',
  NOW() - interval '3 hours'
FROM bookings b
JOIN clients cl ON cl.id = b.client_id
WHERE b.booking_number LIKE 'DEMO-NOV-%'
  AND b.service_date BETWEEN '2026-11-18' AND '2026-11-22';

-- Timeslots на ближайшие дни (занятые слоты)
INSERT INTO timeslots (date, time, is_available, booking_id, created_at)
SELECT b.service_date, b.time, false, b.id, NOW()
FROM bookings b
WHERE b.booking_number LIKE 'DEMO-NOV-%'
  AND b.service_date BETWEEN '2026-11-19' AND '2026-11-22'
  AND b.status NOT IN ('cancelled')
ON CONFLICT DO NOTHING;

COMMIT;

-- Сводка
SELECT 'users' AS entity, COUNT(*) FROM users
UNION ALL SELECT 'clients', COUNT(*) FROM clients
UNION ALL SELECT 'masters', COUNT(*) FROM masters
UNION ALL SELECT 'services', COUNT(*) FROM services
UNION ALL SELECT 'posts', COUNT(*) FROM posts
UNION ALL SELECT 'bookings', COUNT(*) FROM bookings
UNION ALL SELECT 'bookings_nov', COUNT(*) FROM bookings WHERE service_date BETWEEN '2026-11-01' AND '2026-11-30'
UNION ALL SELECT 'promocodes', COUNT(*) FROM promocodes
UNION ALL SELECT 'promotions', COUNT(*) FROM promotions
UNION ALL SELECT 'blocked_slots', COUNT(*) FROM blocked_slots
UNION ALL SELECT 'broadcasts', COUNT(*) FROM broadcasts
UNION ALL SELECT 'settings', COUNT(*) FROM settings
ORDER BY 1;

SELECT status, COUNT(*) FROM bookings WHERE booking_number LIKE 'DEMO-NOV-%' GROUP BY status ORDER BY status;
"""


def main() -> None:
    print(SQL)


if __name__ == "__main__":
    main()
