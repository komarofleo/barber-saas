-- Миграция: Изменение типа столбца status в таблице payments с enum на VARCHAR
-- Дата: 2026-01-06
-- Описание: Изменяет тип столбца status с payment_status (enum) на VARCHAR(20)
--           для совместимости с моделью SQLAlchemy

-- Изменяем тип столбца status на VARCHAR(20)
ALTER TABLE public.payments 
ALTER COLUMN status TYPE VARCHAR(20) 
USING status::text;

-- Комментарий к столбцу
COMMENT ON COLUMN public.payments.status IS 'Статус платежа: pending, processing, succeeded, cancelled, failed, refunded';

