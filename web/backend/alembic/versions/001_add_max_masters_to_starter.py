"""Добавление поля max_masters в таблицу plans и обновление дефолтных значений

Revision ID: 001_add_max_masters_to_starter
Revises: 
Create Date: 2026-01-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import BIGINT

# revision identifiers, used by Alembic.
revision = '001_add_max_masters_to_starter'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляем поле max_masters и обновляем дефолтные значения."""
    
    # Добавляем поле max_masters, если его нет
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем, существует ли столбец max_masters
    columns = [col['name'] for col in inspector.get_columns('public.plans')]
    has_max_masters = 'max_masters' in columns
    
    if not has_max_masters:
        # Добавляем столбец max_masters с дефолтным значением для Starter
        op.add_column('plans', sa.Column(
            'max_masters',
            sa.Integer(),
            server_default='3',
            nullable=True
        ))
        print('[upgrade] Добавлен столбец max_masters с дефолтом 3')
    
    # Обновляем дефолтные значения
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 100,
                max_users = 5,
                max_masters = 3
            WHERE id = 1
        """)
    )
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 300,
                max_users = 10,
                max_masters = 5
            WHERE id = 2
        """)
    )
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 99999,
                max_users = 20,
                max_masters = 10
            WHERE id = 3
        """)
    )
    print('[upgrade] Обновлены значения для всех тарифов')


def downgrade() -> None:
    """Откат изменений."""
    
    # Удаляем столбец max_masters
    op.drop_column('plans', 'max_masters')
    print('[downgrade] Удален столбец max_masters')
    
    # Возврат к исходным значениям
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 50,
                max_users = 5,
                max_masters = 2
            WHERE id = 1
        """)
    )
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 350,
                max_users = 10,
                max_masters = 5
            WHERE id = 2
        """)
    )
    op.execute(
        sa.text("""
            UPDATE plans
            SET max_bookings_per_month = 10000,
                max_users = 20,
                max_masters = 10
            WHERE id = 3
        """)
    )
    print('[downgrade] Возврат к исходным значениям')

