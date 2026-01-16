"""Создать таблицу contract_requests

Revision ID: 003_create_contract_requests
Revises: 002_rename_metadata
Create Date: 2026-01-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "003_create_contract_requests"
down_revision = "002_rename_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создать таблицу заявок на генерацию договора."""
    op.create_table(
        "contract_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_telegram_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new", index=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contract_number", sa.String(length=50), nullable=False),
        sa.Column("contract_date", sa.Date(), nullable=False, index=True),
        sa.Column("daily_seq", sa.Integer(), nullable=False),
        sa.Column("document_path", sa.String(length=500), nullable=True),
        sa.Column("public_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_number", name="uq_contract_requests_number"),
        sa.UniqueConstraint("contract_date", "daily_seq", name="uq_contract_requests_date_seq"),
        schema="public",
    )
    op.create_index(
        "ix_contract_requests_requester_telegram_id",
        "contract_requests",
        ["requester_telegram_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_contract_requests_status",
        "contract_requests",
        ["status"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_contract_requests_contract_date",
        "contract_requests",
        ["contract_date"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    """Удалить таблицу заявок на генерацию договора."""
    op.drop_index("ix_contract_requests_contract_date", table_name="contract_requests", schema="public")
    op.drop_index("ix_contract_requests_status", table_name="contract_requests", schema="public")
    op.drop_index("ix_contract_requests_requester_telegram_id", table_name="contract_requests", schema="public")
    op.drop_table("contract_requests", schema="public")
