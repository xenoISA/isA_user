"""Add order reference and amount breakdown to transactions

Revision ID: pay_002
Revises: pay_001
Create Date: 2026-02-02

Wraps existing SQL migration: 002_add_order_amount_breakdown.sql
"""
from typing import Sequence, Union

from alembic import op

revision: str = "pay_002"
down_revision: Union[str, None] = "pay_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE payment.transactions
            ADD COLUMN IF NOT EXISTS order_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS subtotal_amount DOUBLE PRECISION DEFAULT 0,
            ADD COLUMN IF NOT EXISTS tax_amount DOUBLE PRECISION DEFAULT 0,
            ADD COLUMN IF NOT EXISTS shipping_amount DOUBLE PRECISION DEFAULT 0,
            ADD COLUMN IF NOT EXISTS discount_amount DOUBLE PRECISION DEFAULT 0
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payment.transactions(order_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS payment.idx_payments_order_id")
    op.execute("ALTER TABLE payment.transactions DROP COLUMN IF EXISTS discount_amount")
    op.execute("ALTER TABLE payment.transactions DROP COLUMN IF EXISTS shipping_amount")
    op.execute("ALTER TABLE payment.transactions DROP COLUMN IF EXISTS tax_amount")
    op.execute("ALTER TABLE payment.transactions DROP COLUMN IF EXISTS subtotal_amount")
    op.execute("ALTER TABLE payment.transactions DROP COLUMN IF EXISTS order_id")
