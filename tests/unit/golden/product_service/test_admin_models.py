"""
Unit Tests: Admin Request/Response Models

Tests Pydantic validation for admin CRUD request models.
"""
import pytest
from pydantic import ValidationError

from microservices.product_service.models import (
    AdminCreateProductRequest,
    AdminUpdateProductRequest,
    AdminCreatePricingRequest,
    AdminUpdatePricingRequest,
    ProductType,
)


class TestAdminCreateProductRequest:
    """Test AdminCreateProductRequest validation"""

    def test_valid_create_request(self):
        req = AdminCreateProductRequest(
            product_id="claude-sonnet-4",
            product_name="Claude Sonnet 4",
            product_code="CLAUDE-SONNET-4",
            product_type=ProductType.MODEL_INFERENCE,
            base_price=0.003,
            category="ai_models",
        )
        assert req.product_id == "claude-sonnet-4"
        assert req.product_type == ProductType.MODEL_INFERENCE
        assert req.is_active is True

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AdminCreateProductRequest(product_id="test")

    def test_empty_product_id_rejected(self):
        with pytest.raises(ValidationError):
            AdminCreateProductRequest(
                product_id="",
                product_name="Test",
                product_code="TEST",
                product_type=ProductType.MODEL_INFERENCE,
            )

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            AdminCreateProductRequest(
                product_id="test",
                product_name="Test",
                product_code="TEST",
                product_type=ProductType.MODEL_INFERENCE,
                base_price=-1.0,
            )

    def test_defaults_applied(self):
        req = AdminCreateProductRequest(
            product_id="test",
            product_name="Test",
            product_code="TEST",
            product_type=ProductType.OTHER,
        )
        assert req.currency == "USD"
        assert req.category == "ai_models"
        assert req.features == []
        assert req.metadata == {}
        assert req.is_active is True

    def test_all_fields_populated(self):
        req = AdminCreateProductRequest(
            product_id="test",
            product_name="Test Product",
            product_code="TEST-001",
            description="A test product",
            category="storage",
            product_type=ProductType.STORAGE_MINIO,
            base_price=0.023,
            currency="USD",
            billing_interval="monthly",
            features=["s3_compatible"],
            quota_limits={"max_storage_gb": 100},
            metadata={"provider": "minio"},
            tags=["storage", "s3"],
            is_active=True,
        )
        assert req.features == ["s3_compatible"]
        assert req.tags == ["storage", "s3"]


class TestAdminUpdateProductRequest:
    """Test AdminUpdateProductRequest — all fields optional"""

    def test_empty_update_valid(self):
        req = AdminUpdateProductRequest()
        assert req.product_name is None
        assert req.is_active is None

    def test_partial_update(self):
        req = AdminUpdateProductRequest(
            product_name="Updated Name",
            is_active=False,
        )
        assert req.product_name == "Updated Name"
        assert req.is_active is False
        assert req.description is None

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            AdminUpdateProductRequest(base_price=-5.0)


class TestAdminCreatePricingRequest:
    """Test AdminCreatePricingRequest validation"""

    def test_valid_pricing_request(self):
        req = AdminCreatePricingRequest(
            pricing_id="pricing_test_base",
            tier_name="base",
            unit_price=0.003,
        )
        assert req.pricing_id == "pricing_test_base"
        assert req.currency == "USD"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AdminCreatePricingRequest(tier_name="base")

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            AdminCreatePricingRequest(
                pricing_id="test",
                unit_price=-1.0,
            )


class TestAdminUpdatePricingRequest:
    """Test AdminUpdatePricingRequest — all fields optional"""

    def test_empty_update_valid(self):
        req = AdminUpdatePricingRequest()
        assert req.tier_name is None

    def test_partial_update(self):
        req = AdminUpdatePricingRequest(
            unit_price=0.005,
            metadata={"billing_type": "usage_based"},
        )
        assert req.unit_price == 0.005
        assert req.tier_name is None
