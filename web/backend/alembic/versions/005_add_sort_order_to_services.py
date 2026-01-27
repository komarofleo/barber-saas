"""Добавить поле sort_order в services

Revision ID: 005_add_sort_order_to_services
Revises: 004_company_admin_telegram_bigint
Create Date: 2026-01-20 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_sort_order_to_services'
down_revision = '004_company_admin_telegram_bigint'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поле sort_order в таблицу services для всех tenant схем
    # Сначала для public схемы (если есть)
    op.execute("""
        DO $$
        DECLARE
            schema_name TEXT;
        BEGIN
            -- Добавляем в public схему (если таблица существует)
            IF EXISTS (SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' AND table_name = 'services') THEN
                ALTER TABLE public.services 
                ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;
                CREATE INDEX IF NOT EXISTS ix_services_sort_order ON public.services(sort_order);
                UPDATE public.services SET sort_order = id WHERE sort_order = 0;
            END IF;
            
            -- Добавляем во все tenant схемы
            FOR schema_name IN 
                SELECT nspname FROM pg_namespace 
                WHERE nspname LIKE 'tenant_%'
            LOOP
                IF EXISTS (SELECT 1 FROM information_schema.tables 
                          WHERE table_schema = schema_name AND table_name = 'services') THEN
                    EXECUTE format('ALTER TABLE %I.services ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0', schema_name);
                    EXECUTE format('CREATE INDEX IF NOT EXISTS ix_services_sort_order ON %I.services(sort_order)', schema_name);
                    EXECUTE format('UPDATE %I.services SET sort_order = id WHERE sort_order = 0', schema_name);
                END IF;
            END LOOP;
        END $$;
    """)


def downgrade():
    # Удаляем поле sort_order из всех схем
    op.execute("""
        DO $$
        DECLARE
            schema_name TEXT;
        BEGIN
            -- Удаляем из public схемы
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_schema = 'public' AND table_name = 'services' AND column_name = 'sort_order') THEN
                DROP INDEX IF EXISTS public.ix_services_sort_order;
                ALTER TABLE public.services DROP COLUMN IF EXISTS sort_order;
            END IF;
            
            -- Удаляем из всех tenant схем
            FOR schema_name IN 
                SELECT nspname FROM pg_namespace 
                WHERE nspname LIKE 'tenant_%'
            LOOP
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_schema = schema_name AND table_name = 'services' AND column_name = 'sort_order') THEN
                    EXECUTE format('DROP INDEX IF EXISTS %I.ix_services_sort_order', schema_name);
                    EXECUTE format('ALTER TABLE %I.services DROP COLUMN IF EXISTS sort_order', schema_name);
                END IF;
            END LOOP;
        END $$;
    """)
