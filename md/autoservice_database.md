# ⚠️ УСТАРЕВШИЙ ДОКУМЕНТ (legacy)
Этот файл относится к старой ветке документации “AutoService” и описывает схему с автополями (`car_brand`, `car_model`, `car_number`, `total_visits/total_amount`), которые **не являются актуальными** для Barber SaaS (салон красоты).

**Актуальная документация:**
- `md/README.md` — индекс документации
- `md/00_PROJECT_OVERVIEW.md` — архитектура
- `tasks.md` — единый TODO и текущие проблемы

---

# 🗄️ DATABASE - Структура базы данных Barber

Полное описание схемы базы данных PostgreSQL для системы Barber.

---

## 📋 Содержание

1. [Обзор](#обзор)
2. [Основные таблицы](#основные-таблицы)
3. [Связи между таблицами](#связи-между-таблицами)
4. [Индексы](#индексы)
5. [Триггеры](#триггеры)
6. [Миграции](#миграции)

---

## 🎯 Обзор

**СУБД:** PostgreSQL 15  
**ORM:** SQLAlchemy 2.0 (async)  
**Миграции:** Alembic  
**Кодировка:** UTF-8  
**Часовой пояс:** Europe/Moscow

### Список таблиц

```
users               - Пользователи (клиенты + мастера + админы)
clients             - Дополнительная информация о клиентах
masters             - Мастера
services            - Услуги
master_services     - Специализация мастеров (many-to-many)
posts               - Рабочие места
bookings            - Записи
booking_history     - История изменений записей
client_history      - История обслуживания клиентов
timeslots           - Временные слоты (для быстрого поиска)
blocked_slots       - Блокировки
promocodes          - Промокоды
promotions          - Акции
notifications       - История уведомлений
broadcasts          - Рассылки
settings            - Настройки системы
```

---

## 📊 Основные таблицы

### 1. users - Пользователи

Базовая таблица для всех пользователей системы.

```sql
CREATE TABLE users (
    id                  SERIAL PRIMARY KEY,
    telegram_id         BIGINT UNIQUE NOT NULL,
    username            VARCHAR(255),
    first_name          VARCHAR(255),
    last_name           VARCHAR(255),
    phone               VARCHAR(20),
    is_admin            BOOLEAN DEFAULT FALSE,
    is_master           BOOLEAN DEFAULT FALSE,
    is_blocked          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Пользователи системы';
COMMENT ON COLUMN users.telegram_id IS 'Telegram ID пользователя (уникальный)';
COMMENT ON COLUMN users.is_admin IS 'Является ли администратором';
COMMENT ON COLUMN users.is_master IS 'Является ли мастером';
COMMENT ON COLUMN users.is_blocked IS 'Заблокирован ли пользователь';
```

**Индексы:**
```sql
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_phone ON users(phone);
```

---

### 2. clients - Клиенты

Дополнительная информация о клиентах (расширение таблицы users).

```sql
CREATE TABLE clients (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
    full_name           VARCHAR(255) NOT NULL,
    phone               VARCHAR(20) NOT NULL,
    car_brand           VARCHAR(100),
    car_model           VARCHAR(100),
    car_number          VARCHAR(20),
    total_visits        INTEGER DEFAULT 0,
    total_amount        DECIMAL(10,2) DEFAULT 0,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE clients IS 'Информация о клиентах';
COMMENT ON COLUMN clients.total_visits IS 'Общее количество визитов';
COMMENT ON COLUMN clients.total_amount IS 'Общая сумма покупок';
```

**Индексы:**
```sql
CREATE INDEX idx_clients_user_id ON clients(user_id);
CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_car_number ON clients(car_number);
```

---

### 3. masters - Мастера

Информация о мастерах салона красоты.

```sql
CREATE TABLE masters (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
    full_name           VARCHAR(255) NOT NULL,
    phone               VARCHAR(20),
    telegram_id         BIGINT,
    is_universal        BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE masters IS 'Мастера салона красоты';
COMMENT ON COLUMN masters.is_universal IS 'Универсальный (делает все услуги) или специализированный';
```

**Индексы:**
```sql
CREATE INDEX idx_masters_user_id ON masters(user_id);
CREATE INDEX idx_masters_telegram_id ON masters(telegram_id);
```

---

### 4. services - Услуги

Список услуг салона красоты.

```sql
CREATE TABLE services (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    duration            INTEGER NOT NULL,
    price               DECIMAL(10,2) NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE services IS 'Услуги салона красоты';
COMMENT ON COLUMN services.duration IS 'Длительность в минутах (30 или 60)';
COMMENT ON COLUMN services.price IS 'Базовая цена услуги';
COMMENT ON COLUMN services.is_active IS 'Активна ли услуга (показывается клиентам)';
```

**Индексы:**
```sql
CREATE INDEX idx_services_is_active ON services(is_active);
```

**Примеры данных:**
```sql
INSERT INTO services (name, description, duration, price) VALUES
('ТО', 'Техническое обслуживание автомобиля', 60, 3000),
('Диагностика', 'Компьютерная диагностика', 30, 1500),
('Ремонт двигателя', 'Ремонт и обслуживание двигателя', 60, 5000),
('Шиномонтаж', 'Шиномонтаж и балансировка', 30, 2000),
('Кузовной ремонт', 'Ремонт кузова', 60, 8000),
('Электрика', 'Ремонт электрики', 60, 4000);
```

---

### 5. master_services - Специализация мастеров

Связь many-to-many между мастерами и услугами (для специализации).

```sql
CREATE TABLE master_services (
    id                  SERIAL PRIMARY KEY,
    master_id           INTEGER REFERENCES masters(id) ON DELETE CASCADE,
    service_id          INTEGER REFERENCES services(id) ON DELETE CASCADE,
    created_at          TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(master_id, service_id)
);

COMMENT ON TABLE master_services IS 'Специализация мастеров (какие услуги может делать мастер)';
```

**Индексы:**
```sql
CREATE INDEX idx_master_services_master ON master_services(master_id);
CREATE INDEX idx_master_services_service ON master_services(service_id);
```

**Примечание:** Если `masters.is_universal = TRUE`, то эта таблица игнорируется (мастер делает все услуги).

---

### 6. posts - Рабочие места

Рабочие места для обслуживания клиентов.

```sql
CREATE TABLE posts (
    id                  SERIAL PRIMARY KEY,
    number              INTEGER NOT NULL UNIQUE,
    name                VARCHAR(255),
    description         TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE posts IS 'Посты/боксы автосервиса';
COMMENT ON COLUMN posts.number IS 'Номер поста (уникальный)';
```

**Примеры данных:**
```sql
INSERT INTO posts (number, name) VALUES
(1, 'Пост №1'),
(2, 'Пост №2'),
(3, 'Пост №3'),
(4, 'Пост №4'),
(5, 'Пост №5');
```

---

### 7. bookings - Записи

Главная таблица с записями клиентов.

```sql
CREATE TABLE bookings (
    id                  SERIAL PRIMARY KEY,
    booking_number      VARCHAR(50) UNIQUE NOT NULL,
    client_id           INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    service_id          INTEGER REFERENCES services(id) ON DELETE SET NULL,
    master_id           INTEGER REFERENCES masters(id) ON DELETE SET NULL,
    post_id             INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    
    date                DATE NOT NULL,
    time                TIME NOT NULL,
    duration            INTEGER NOT NULL,
    end_time            TIME NOT NULL,
    
    status              VARCHAR(50) DEFAULT 'new',
    
    amount              DECIMAL(10,2),
    is_paid             BOOLEAN DEFAULT FALSE,
    payment_method      VARCHAR(50),
    
    promocode_id        INTEGER REFERENCES promocodes(id) ON DELETE SET NULL,
    discount_amount     DECIMAL(10,2) DEFAULT 0,
    
    comment             TEXT,
    admin_comment       TEXT,
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    confirmed_at        TIMESTAMP,
    completed_at        TIMESTAMP,
    cancelled_at        TIMESTAMP
);

COMMENT ON TABLE bookings IS 'Записи клиентов';
COMMENT ON COLUMN bookings.booking_number IS 'Номер записи для клиента (например: B-20251227-001)';
COMMENT ON COLUMN bookings.duration IS 'Длительность в минутах';
COMMENT ON COLUMN bookings.end_time IS 'Время окончания (вычисляется автоматически)';
COMMENT ON COLUMN bookings.status IS 'Статус: new, confirmed, completed, cancelled, no_show, priority';
COMMENT ON COLUMN bookings.payment_method IS 'Способ оплаты: cash, card, qr';
```

**Индексы:**
```sql
CREATE INDEX idx_bookings_date ON bookings(date);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_client ON bookings(client_id);
CREATE INDEX idx_bookings_master ON bookings(master_id);
CREATE INDEX idx_bookings_post ON bookings(post_id);
CREATE INDEX idx_bookings_service ON bookings(service_id);
CREATE INDEX idx_bookings_date_time ON bookings(date, time);
CREATE INDEX idx_bookings_booking_number ON bookings(booking_number);
```

**Триггер для генерации booking_number:**
```sql
CREATE OR REPLACE FUNCTION generate_booking_number()
RETURNS TRIGGER AS $$
DECLARE
    date_str TEXT;
    counter INTEGER;
BEGIN
    IF NEW.booking_number IS NULL THEN
        date_str := TO_CHAR(NEW.date, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(CAST(SUBSTRING(booking_number FROM 12) AS INTEGER)), 0) + 1
        INTO counter
        FROM bookings
        WHERE booking_number LIKE 'B-' || date_str || '-%';
        
        NEW.booking_number := 'B-' || date_str || '-' || LPAD(counter::TEXT, 3, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_booking_number
BEFORE INSERT ON bookings
FOR EACH ROW
EXECUTE FUNCTION generate_booking_number();
```

---

### 8. booking_history - История изменений записей

Лог всех изменений в записях.

```sql
CREATE TABLE booking_history (
    id                  SERIAL PRIMARY KEY,
    booking_id          INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
    changed_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    field_name          VARCHAR(100) NOT NULL,
    old_value           TEXT,
    new_value           TEXT,
    changed_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE booking_history IS 'История изменений записей';
COMMENT ON COLUMN booking_history.field_name IS 'Название измененного поля';
```

**Индексы:**
```sql
CREATE INDEX idx_booking_history_booking ON booking_history(booking_id);
CREATE INDEX idx_booking_history_changed_at ON booking_history(changed_at);
```

---

### 9. client_history - История обслуживания

История всех визитов клиента.

```sql
CREATE TABLE client_history (
    id                  SERIAL PRIMARY KEY,
    client_id           INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    booking_id          INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
    service_id          INTEGER REFERENCES services(id) ON DELETE SET NULL,
    master_id           INTEGER REFERENCES masters(id) ON DELETE SET NULL,
    date                DATE NOT NULL,
    amount              DECIMAL(10,2),
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE client_history IS 'История обслуживания клиентов';
```

**Индексы:**
```sql
CREATE INDEX idx_client_history_client ON client_history(client_id);
CREATE INDEX idx_client_history_date ON client_history(date);
```

---

### 10. timeslots - Временные слоты

Вспомогательная таблица для быстрого поиска доступных слотов.

```sql
CREATE TABLE timeslots (
    id                  SERIAL PRIMARY KEY,
    date                DATE NOT NULL,
    time                TIME NOT NULL,
    is_available        BOOLEAN DEFAULT TRUE,
    booking_id          INTEGER REFERENCES bookings(id) ON DELETE SET NULL,
    created_at          TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(date, time)
);

COMMENT ON TABLE timeslots IS 'Временные слоты для быстрого поиска';
```

**Индексы:**
```sql
CREATE INDEX idx_timeslots_date ON timeslots(date);
CREATE INDEX idx_timeslots_date_time ON timeslots(date, time);
CREATE INDEX idx_timeslots_available ON timeslots(is_available);
```

---

### 11. blocked_slots - Блокировки

Блокировки дат, времени, мастеров, постов, услуг.

```sql
CREATE TABLE blocked_slots (
    id                  SERIAL PRIMARY KEY,
    block_type          VARCHAR(50) NOT NULL,
    
    master_id           INTEGER REFERENCES masters(id) ON DELETE CASCADE,
    post_id             INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    service_id          INTEGER REFERENCES services(id) ON DELETE CASCADE,
    
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    start_time          TIME,
    end_time            TIME,
    
    reason              TEXT,
    created_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE blocked_slots IS 'Блокировки (даты, мастера, посты, услуги)';
COMMENT ON COLUMN blocked_slots.block_type IS 'Тип: full_service, master, post, service';
COMMENT ON COLUMN blocked_slots.start_time IS 'Если NULL, то блокировка на весь день';
```

**Индексы:**
```sql
CREATE INDEX idx_blocks_dates ON blocked_slots(start_date, end_date);
CREATE INDEX idx_blocks_type ON blocked_slots(block_type);
CREATE INDEX idx_blocks_master ON blocked_slots(master_id);
CREATE INDEX idx_blocks_post ON blocked_slots(post_id);
CREATE INDEX idx_blocks_service ON blocked_slots(service_id);
```

---

### 12. promocodes - Промокоды

Промокоды для скидок.

```sql
CREATE TABLE promocodes (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(50) UNIQUE NOT NULL,
    discount_type       VARCHAR(20) NOT NULL,
    discount_value      DECIMAL(10,2) NOT NULL,
    service_id          INTEGER REFERENCES services(id) ON DELETE CASCADE,
    
    min_amount          DECIMAL(10,2) DEFAULT 0,
    max_uses            INTEGER,
    current_uses        INTEGER DEFAULT 0,
    start_date          DATE,
    end_date            DATE,
    is_active           BOOLEAN DEFAULT TRUE,
    description         TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE promocodes IS 'Промокоды';
COMMENT ON COLUMN promocodes.discount_type IS 'Тип скидки: percent, fixed';
COMMENT ON COLUMN promocodes.service_id IS 'Если NULL, то на все услуги';
COMMENT ON COLUMN promocodes.max_uses IS 'Если NULL, то безлимит';
```

**Индексы:**
```sql
CREATE INDEX idx_promocodes_code ON promocodes(code);
CREATE INDEX idx_promocodes_active ON promocodes(is_active);
```

---

### 13. promotions - Акции

Акции на услуги.

```sql
CREATE TABLE promotions (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    discount_type       VARCHAR(20) NOT NULL,
    discount_value      DECIMAL(10,2) NOT NULL,
    service_id          INTEGER REFERENCES services(id) ON DELETE CASCADE,
    
    start_date          DATE,
    end_date            DATE,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE promotions IS 'Акции на услуги';
COMMENT ON COLUMN promotions.discount_type IS 'Тип скидки: percent, fixed';
COMMENT ON COLUMN promotions.service_id IS 'Если NULL, то на все услуги';
```

**Индексы:**
```sql
CREATE INDEX idx_promotions_active ON promotions(is_active);
CREATE INDEX idx_promotions_dates ON promotions(start_date, end_date);
```

---

### 14. notifications - История уведомлений

Лог всех отправленных уведомлений.

```sql
CREATE TABLE notifications (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
    booking_id          INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
    notification_type   VARCHAR(50) NOT NULL,
    message             TEXT NOT NULL,
    is_sent             BOOLEAN DEFAULT FALSE,
    sent_at             TIMESTAMP,
    error_message       TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE notifications IS 'История уведомлений';
COMMENT ON COLUMN notifications.notification_type IS 'Тип: reminder_day, reminder_hour, status_change, confirmation, work_order, etc.';
```

**Индексы:**
```sql
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_booking ON notifications(booking_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_sent ON notifications(is_sent);
```

---

### 15. broadcasts - Рассылки

Массовые рассылки клиентам.

```sql
CREATE TABLE broadcasts (
    id                  SERIAL PRIMARY KEY,
    text                TEXT NOT NULL,
    image_path          VARCHAR(500),
    target_audience     VARCHAR(50) NOT NULL,
    filter_params       JSONB,
    status              VARCHAR(50) DEFAULT 'pending',
    
    total_sent          INTEGER DEFAULT 0,
    total_errors        INTEGER DEFAULT 0,
    created_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP DEFAULT NOW(),
    sent_at             TIMESTAMP
);

COMMENT ON TABLE broadcasts IS 'Рассылки';
COMMENT ON COLUMN broadcasts.target_audience IS 'Аудитория: all, active, new, by_service';
COMMENT ON COLUMN broadcasts.filter_params IS 'Параметры фильтрации (JSON)';
COMMENT ON COLUMN broadcasts.status IS 'Статус: pending, sending, completed, failed';
```

**Индексы:**
```sql
CREATE INDEX idx_broadcasts_status ON broadcasts(status);
CREATE INDEX idx_broadcasts_created_at ON broadcasts(created_at);
```

---

### 16. settings - Настройки системы

Ключ-значение для настроек.

```sql
CREATE TABLE settings (
    id                  SERIAL PRIMARY KEY,
    key                 VARCHAR(100) UNIQUE NOT NULL,
    value               TEXT,
    description         TEXT,
    updated_at          TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE settings IS 'Настройки системы';
```

**Примеры настроек:**
```sql
INSERT INTO settings (key, value, description) VALUES
('accepting_bookings', 'true', 'Принимаются ли заявки (глобальная блокировка)'),
('work_start_time', '09:00', 'Время начала работы'),
('work_end_time', '18:00', 'Время окончания работы'),
('slot_duration', '30', 'Длительность слота в минутах'),
('enable_master_specialization', 'false', 'Учитывать специализацию мастеров'),
('reminder_day_before_time', '18:00', 'Время напоминания за день'),
('reminder_hour_before', 'true', 'Напоминание за час'),
('notify_admin_delay_minutes', '5', 'Задержка уведомления админу'),
('work_order_time', '08:00', 'Время отправки лист-наряда мастерам');
```

---

## 🔗 Связи между таблицами

### Диаграмма связей

```
users (1) ─────< (∞) clients
users (1) ─────< (∞) masters
users (1) ─────< (∞) bookings (created_by)

masters (∞) ────< master_services >──── (∞) services
masters (1) ─────< (∞) bookings
services (1) ─────< (∞) bookings
posts (1) ─────< (∞) bookings
clients (1) ─────< (∞) bookings
promocodes (1) ─────< (∞) bookings

bookings (1) ─────< (∞) booking_history
bookings (1) ─────< (∞) client_history
bookings (1) ─────< (∞) notifications

masters (1) ─────< (∞) blocked_slots
posts (1) ─────< (∞) blocked_slots
services (1) ─────< (∞) blocked_slots
```

---

## 📈 Производительность и оптимизация

### Основные индексы

Все основные индексы уже описаны выше в секциях таблиц.

### Дополнительные составные индексы

```sql
-- Быстрый поиск записей по дате и статусу
CREATE INDEX idx_bookings_date_status ON bookings(date, status);

-- Быстрый поиск доступных слотов
CREATE INDEX idx_timeslots_date_available ON timeslots(date, is_available);

-- Быстрый поиск активных промокодов
CREATE INDEX idx_promocodes_active_dates ON promocodes(is_active, start_date, end_date);
```

### Партиционирование (опционально для большой нагрузки)

```sql
-- Партиционирование таблицы bookings по годам
CREATE TABLE bookings_2025 PARTITION OF bookings
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE bookings_2026 PARTITION OF bookings
FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

---

## 🔄 Миграции

Миграции управляются через Alembic.

### Создание миграции

```bash
# Автоматическая генерация
alembic revision --autogenerate -m "описание изменений"

# Ручная миграция
alembic revision -m "описание изменений"
```

### Применение миграций

```bash
# Применить все
alembic upgrade head

# Откатить одну
alembic downgrade -1

# Откатить все
alembic downgrade base
```

### История миграций

```
001_initial - Создание базовых таблиц
002_add_booking_history - Добавление истории изменений
003_add_blocked_slots - Добавление блокировок
004_add_promocodes - Добавление промокодов
005_add_settings - Добавление настроек
```

---

## 📝 Примечания

- Все даты и время хранятся в UTC
- Конвертация в Europe/Moscow происходит на уровне приложения
- Soft delete не используется (ON DELETE CASCADE)
- JSONB используется для гибких параметров (filter_params в broadcasts)
- Decimal(10,2) для денежных значений

---

**Версия БД:** 1.0.0  
**Последнее обновление:** 27 декабря 2025