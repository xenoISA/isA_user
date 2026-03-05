"""Initial payment service schema

Revision ID: pay_001
Revises: None
Create Date: 2025-10-27

Wraps existing SQL migration: 001_create_payment_schema.sql
"""
from typing import Sequence, Union

from alembic import op

revision: str = "pay_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS payment")

    # subscription_plans
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.subscription_plans (
            id SERIAL PRIMARY KEY,
            plan_id VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            tier VARCHAR(50) NOT NULL,
            price_usd DOUBLE PRECISION NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            billing_cycle VARCHAR(20) NOT NULL,
            features JSONB DEFAULT '{}'::jsonb,
            credits_included INTEGER DEFAULT 0,
            max_users INTEGER,
            max_storage_gb INTEGER,
            trial_days INTEGER DEFAULT 0,
            stripe_price_id VARCHAR(255),
            stripe_product_id VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            is_public BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # payment_methods
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.payment_methods (
            id SERIAL PRIMARY KEY,
            method_id VARCHAR(255) NOT NULL UNIQUE,
            user_id VARCHAR(255) NOT NULL,
            method_type VARCHAR(50) NOT NULL,
            is_default BOOLEAN DEFAULT false,
            is_verified BOOLEAN DEFAULT false,
            stripe_payment_method_id VARCHAR(255),
            card_last4 VARCHAR(4),
            card_brand VARCHAR(50),
            card_exp_month INTEGER,
            card_exp_year INTEGER,
            bank_name VARCHAR(255),
            bank_account_last4 VARCHAR(4),
            external_account_id VARCHAR(255),
            billing_details JSONB DEFAULT '{}'::jsonb,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # subscriptions
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.subscriptions (
            id SERIAL PRIMARY KEY,
            subscription_id VARCHAR(255) NOT NULL UNIQUE,
            user_id VARCHAR(255) NOT NULL,
            organization_id VARCHAR(255),
            plan_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            tier VARCHAR(50) NOT NULL,
            current_period_start TIMESTAMPTZ NOT NULL,
            current_period_end TIMESTAMPTZ NOT NULL,
            billing_cycle VARCHAR(20) NOT NULL,
            cancel_at_period_end BOOLEAN DEFAULT false,
            canceled_at TIMESTAMPTZ,
            cancellation_reason TEXT,
            trial_start TIMESTAMPTZ,
            trial_end TIMESTAMPTZ,
            stripe_subscription_id VARCHAR(255),
            stripe_customer_id VARCHAR(255),
            payment_method_id VARCHAR(255),
            last_payment_date TIMESTAMPTZ,
            next_payment_date TIMESTAMPTZ,
            quantity INTEGER DEFAULT 1,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT fk_subscription_plan FOREIGN KEY (plan_id)
                REFERENCES payment.subscription_plans(plan_id) ON DELETE RESTRICT
        )
    """)

    # transactions
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.transactions (
            id SERIAL PRIMARY KEY,
            payment_id VARCHAR(255) NOT NULL UNIQUE,
            user_id VARCHAR(255) NOT NULL,
            organization_id VARCHAR(255),
            subscription_id VARCHAR(255),
            invoice_id VARCHAR(255),
            amount DOUBLE PRECISION NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            status VARCHAR(50) NOT NULL,
            payment_method VARCHAR(50),
            description TEXT,
            processor VARCHAR(50) DEFAULT 'stripe',
            processor_payment_id VARCHAR(255),
            processor_response JSONB DEFAULT '{}'::jsonb,
            failure_reason TEXT,
            failure_code VARCHAR(100),
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            paid_at TIMESTAMPTZ,
            failed_at TIMESTAMPTZ
        )
    """)

    # invoices
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.invoices (
            id SERIAL PRIMARY KEY,
            invoice_id VARCHAR(255) NOT NULL UNIQUE,
            invoice_number VARCHAR(100) NOT NULL UNIQUE,
            user_id VARCHAR(255) NOT NULL,
            organization_id VARCHAR(255),
            subscription_id VARCHAR(255),
            payment_intent_id VARCHAR(255),
            payment_method_id VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            amount_total DOUBLE PRECISION NOT NULL,
            amount_paid DOUBLE PRECISION DEFAULT 0,
            amount_due DOUBLE PRECISION NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            description TEXT,
            billing_reason VARCHAR(100),
            billing_period_start TIMESTAMPTZ,
            billing_period_end TIMESTAMPTZ,
            due_date TIMESTAMPTZ,
            stripe_invoice_id VARCHAR(255),
            line_items JSONB DEFAULT '[]'::jsonb,
            tax_amount DOUBLE PRECISION DEFAULT 0,
            discount_amount DOUBLE PRECISION DEFAULT 0,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            paid_at TIMESTAMPTZ,
            voided_at TIMESTAMPTZ
        )
    """)

    # refunds
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment.refunds (
            id SERIAL PRIMARY KEY,
            refund_id VARCHAR(255) NOT NULL UNIQUE,
            payment_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            status VARCHAR(50) NOT NULL,
            reason VARCHAR(255),
            description TEXT,
            processor VARCHAR(50) DEFAULT 'stripe',
            processor_refund_id VARCHAR(255),
            processor_response JSONB DEFAULT '{}'::jsonb,
            requested_by VARCHAR(255),
            approved_by VARCHAR(255),
            requested_at TIMESTAMPTZ DEFAULT NOW(),
            processed_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_plans_tier ON payment.subscription_plans(tier)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_plans_active ON payment.subscription_plans(is_active) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_methods_user ON payment.payment_methods(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_methods_default ON payment.payment_methods(user_id, is_default) WHERE is_default = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON payment.subscriptions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_org ON payment.subscriptions(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON payment.subscriptions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON payment.subscriptions(tier)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_period_end ON payment.subscriptions(current_period_end)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON payment.subscriptions(stripe_subscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payment.transactions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_subscription ON payment.transactions(subscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payment.transactions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_created ON payment.transactions(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_stripe_intent ON payment.transactions(processor_payment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_organization ON payment.transactions(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_user ON payment.invoices(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_subscription ON payment.invoices(subscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON payment.invoices(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON payment.invoices(due_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON payment.invoices(invoice_number)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invoices_organization ON payment.invoices(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refunds_payment ON payment.refunds(payment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refunds_user ON payment.refunds(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refunds_status ON payment.refunds(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refunds_requested_at ON payment.refunds(requested_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment.refunds CASCADE")
    op.execute("DROP TABLE IF EXISTS payment.invoices CASCADE")
    op.execute("DROP TABLE IF EXISTS payment.transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS payment.subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS payment.payment_methods CASCADE")
    op.execute("DROP TABLE IF EXISTS payment.subscription_plans CASCADE")
    op.execute("DROP SCHEMA IF EXISTS payment CASCADE")
