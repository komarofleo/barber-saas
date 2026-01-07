"""Обновление дефолтных значений тарифов в таблице plans

Revision ID: update_plan_defaults
Revises: 
Create Date: 2026-01-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_plan_defaults'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Обновление дефолтных значений max_bookings_per_month, max_users, max_masters в таблице plans."""
    
    # Starter план (id=1)
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 100, "
            "max_users = 5, "
            "max_masters = 3 "
            "WHERE id = 1"
        )
    )
    
    # Pro план (id=2)
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 300, "
            "max_users = 10, "
            "max_masters = 5 "
            "WHERE id = 2"
        )
    )
    
    # Business план (id=3)
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 99999, "
            "max_users = 20, "
            "max_masters = 10 "
            "WHERE id = 3"
        )
    )


def downgrade() -> None:
    """Откат изменений."""
    
    # Возврат к исходным значениям
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 50, "
            "max_users = 5, "
            "max_masters = 2 "
            "WHERE id = 1"
        )
    )
    
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 350, "
            "max_users = 10, "
            "max_masters = 5 "
            "WHERE id = 2"
        )
    )
    
    op.execute(
        sa.text(
            "UPDATE plans "
            "SET max_bookings_per_month = 10000, "
            "max_users = 20, "
            "max_masters = 10 "
            "WHERE id = 3"
        )
    )

