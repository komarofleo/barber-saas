"""Изменить admin_telegram_id на bigint.

Revision ID: 004_company_admin_telegram_bigint
Revises: 003_update_bookings_dates, 003_create_contract_requests
Create Date: 2026-01-17
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "004_company_admin_telegram_bigint"
down_revision = ("003_update_bookings_dates", "003_create_contract_requests")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Перевести admin_telegram_id и telegram_admin_ids в bigint."""
    op.execute(
        """
        ALTER TABLE public.companies
        ALTER COLUMN admin_telegram_id TYPE BIGINT;
        """
    )
    op.execute(
        """
        ALTER TABLE public.companies
        ALTER COLUMN telegram_admin_ids TYPE BIGINT[]
        USING telegram_admin_ids::BIGINT[];
        """
    )


def downgrade() -> None:
    """Вернуть admin_telegram_id и telegram_admin_ids в integer."""
    op.execute(
        """
        ALTER TABLE public.companies
        ALTER COLUMN admin_telegram_id TYPE INTEGER;
        """
    )
    op.execute(
        """
        ALTER TABLE public.companies
        ALTER COLUMN telegram_admin_ids TYPE INTEGER[]
        USING telegram_admin_ids::INTEGER[];
        """
    )
