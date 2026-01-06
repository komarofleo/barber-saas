"""Переименовать metadata в extra_data

Revision ID: 002_rename_metadata
Revises: 001_create_multi_tenant_tables
Create Date: 2026-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_rename_metadata'
down_revision = '001_create_multi_tenant_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Переименовать колонки metadata в extra_data"""
    # Переименовать в subscriptions
    op.execute("ALTER TABLE public.subscriptions RENAME COLUMN metadata TO extra_data")
    
    # Переименовать в payments
    op.execute("ALTER TABLE public.payments RENAME COLUMN metadata TO extra_data")


def downgrade():
    """Вернуть обратно extra_data в metadata"""
    # Вернуть обратно в subscriptions
    op.execute("ALTER TABLE public.subscriptions RENAME COLUMN extra_data TO metadata")
    
    # Вернуть обратно в payments
    op.execute("ALTER TABLE public.payments RENAME COLUMN extra_data TO metadata")

