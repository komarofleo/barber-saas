"""Обновить таблицу bookings: service_date/request_date, удалить telegram_id.

Revision ID: 003_update_bookings_dates
Revises: 002_rename_metadata
Create Date: 2026-01-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_update_bookings_dates"
down_revision = "002_rename_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Обновить таблицы bookings во всех схемах."""
    op.execute(
        """
        DO $$
        DECLARE
            schema_name TEXT;
        BEGIN
            FOR schema_name IN
                SELECT nspname
                FROM pg_namespace
                WHERE nspname = 'public' OR nspname LIKE 'tenant_%'
            LOOP
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = schema_name AND table_name = 'bookings'
                ) THEN
                    -- Удаляем telegram_id, если он есть
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'telegram_id'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I.bookings DROP COLUMN telegram_id', schema_name);
                    END IF;

                    -- Переименовываем date -> service_date, если service_date отсутствует
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'date'
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'service_date'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I.bookings RENAME COLUMN date TO service_date', schema_name);
                    END IF;

                    -- Если request_date раньше использовался как дата услуги, переименовываем его
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'request_date'
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'service_date'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I.bookings RENAME COLUMN request_date TO service_date', schema_name);
                    END IF;

                    -- Добавляем request_date (дата принятия заявки)
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'request_date'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I.bookings ADD COLUMN request_date date', schema_name);
                        EXECUTE format('UPDATE %I.bookings SET request_date = CURRENT_DATE WHERE request_date IS NULL', schema_name);
                        EXECUTE format('ALTER TABLE %I.bookings ALTER COLUMN request_date SET NOT NULL', schema_name);
                    END IF;
                END IF;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Откат миграции (частично)."""
    op.execute(
        """
        DO $$
        DECLARE
            schema_name TEXT;
        BEGIN
            FOR schema_name IN
                SELECT nspname
                FROM pg_namespace
                WHERE nspname = 'public' OR nspname LIKE 'tenant_%'
            LOOP
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = schema_name AND table_name = 'bookings'
                ) THEN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = 'bookings'
                          AND column_name = 'request_date'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I.bookings DROP COLUMN request_date', schema_name);
                    END IF;
                END IF;
            END LOOP;
        END $$;
        """
    )
