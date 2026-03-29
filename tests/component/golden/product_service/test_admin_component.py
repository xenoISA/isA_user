"""
Product Service - Admin Component Tests

Tests admin service methods with mocked repository.
Covers: product CRUD, pricing CRUD, cost definition rotation,
        catalog alignment.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from microservices.product_service.product_service import ProductService
from microservices.product_service.models import (
    Product, ProductType, PricingType, Currency,
    AdminCreateProductRequest, AdminUpdateProductRequest,
    AdminCreatePricingRequest, AdminUpdatePricingRequest,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

def make_mock_product(product_id="test-model", is_active=True):
    return Product(
        product_id=product_id,
        category_id="ai_models",
        name="Test Model",
        product_code=f"TEST-{product_id.upper()}",
        product_type=ProductType.MODEL_INFERENCE,
        base_price=Decimal("0.003"),
        currency=Currency.USD,
        is_active=is_active,
    )


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_product = AsyncMock(return_value=None)
    repo.create_product = AsyncMock()
    repo.update_product = AsyncMock()
    repo.admin_soft_delete_product = AsyncMock(return_value=True)
    repo.admin_create_pricing = AsyncMock()
    repo.admin_get_pricing = AsyncMock()
    repo.admin_update_pricing = AsyncMock()
    repo.get_cost_definitions = AsyncMock(return_value=[])
    repo.get_cost_definition = AsyncMock(return_value=None)
    repo.create_cost_definition = AsyncMock()
    repo.update_cost_definition = AsyncMock()
    repo.expire_cost_definition = AsyncMock(return_value=True)
    repo.get_cost_history = AsyncMock(return_value=[])
    repo.get_catalog_alignment = AsyncMock(return_value={"aligned": True})
    return repo


@pytest.fixture
def service(mock_repo):
    svc = ProductService.__new__(ProductService)
    svc.repository = mock_repo
    svc.event_bus = None
    svc.account_client = None
    svc.organization_client = None
    return svc


# ============================================================================
# Admin Product CRUD
# ============================================================================

class TestAdminCreateProduct:

    async def test_create_product_calls_repository(self, service, mock_repo):
        mock_repo.create_product.return_value = make_mock_product("new-model")
        data = AdminCreateProductRequest(
            product_id="new-model", product_name="New Model",
            product_code="NEW-MODEL", product_type=ProductType.MODEL_INFERENCE,
        ).model_dump()
        result = await service.admin_create_product(data)
        assert result is not None
        mock_repo.create_product.assert_called_once()

    async def test_create_product_passes_correct_fields(self, service, mock_repo):
        mock_repo.create_product.return_value = make_mock_product()
        data = {
            "product_id": "test", "product_name": "Test", "product_code": "TEST",
            "product_type": "model_inference", "base_price": 0.005, "currency": "USD",
            "features": ["vision"], "metadata": {"provider": "openai"},
        }
        await service.admin_create_product(data)
        call_args = mock_repo.create_product.call_args[0][0]
        assert call_args.product_id == "test"

    async def test_create_product_propagates_exception(self, service, mock_repo):
        mock_repo.create_product.side_effect = Exception("DB error")
        with pytest.raises(Exception, match="DB error"):
            await service.admin_create_product({
                "product_id": "x", "product_name": "X", "product_type": "other",
            })


class TestAdminUpdateProduct:

    async def test_update_returns_none_when_not_found(self, service, mock_repo):
        mock_repo.get_product.return_value = None
        result = await service.admin_update_product("missing", {"product_name": "New"})
        assert result is None
        mock_repo.update_product.assert_not_called()

    async def test_update_calls_repository_with_changes(self, service, mock_repo):
        mock_repo.get_product.return_value = make_mock_product()
        mock_repo.update_product.return_value = make_mock_product()
        result = await service.admin_update_product("test-model", {"product_name": "Updated"})
        assert result is not None
        mock_repo.update_product.assert_called_once()

    async def test_update_skips_empty_updates(self, service, mock_repo):
        mock_repo.get_product.return_value = make_mock_product()
        result = await service.admin_update_product("test-model", {})
        assert result is not None
        mock_repo.update_product.assert_not_called()


class TestAdminDeleteProduct:

    async def test_delete_returns_false_when_not_found(self, service, mock_repo):
        mock_repo.get_product.return_value = None
        result = await service.admin_delete_product("missing")
        assert result is False

    async def test_delete_calls_soft_delete(self, service, mock_repo):
        mock_repo.get_product.return_value = make_mock_product()
        result = await service.admin_delete_product("test-model")
        assert result is True
        mock_repo.admin_soft_delete_product.assert_called_once_with("test-model")


# ============================================================================
# Admin Pricing CRUD
# ============================================================================

class TestAdminCreatePricing:

    async def test_create_pricing_returns_none_when_product_missing(self, service, mock_repo):
        mock_repo.get_product.return_value = None
        result = await service.admin_create_pricing("missing", {
            "pricing_id": "p1", "unit_price": 0.003,
        })
        assert result is None

    async def test_create_pricing_delegates_to_repository(self, service, mock_repo):
        mock_repo.get_product.return_value = make_mock_product()
        mock_repo.admin_create_pricing.return_value = {"pricing_id": "p1"}
        result = await service.admin_create_pricing("test-model", {
            "pricing_id": "p1", "tier_name": "base", "unit_price": 0.003,
        })
        assert result == {"pricing_id": "p1"}
        mock_repo.admin_create_pricing.assert_called_once()


class TestAdminUpdatePricing:

    async def test_update_pricing_returns_none_when_missing(self, service, mock_repo):
        mock_repo.admin_get_pricing.return_value = None
        result = await service.admin_update_pricing("missing", {"unit_price": 0.005})
        assert result is None

    async def test_update_pricing_delegates_to_repository(self, service, mock_repo):
        mock_repo.admin_get_pricing.return_value = {"pricing_id": "p1", "unit_price": 0.003}
        mock_repo.admin_update_pricing.return_value = {"pricing_id": "p1", "unit_price": 0.005}
        result = await service.admin_update_pricing("p1", {"unit_price": 0.005})
        assert result["unit_price"] == 0.005

    async def test_update_pricing_returns_existing_when_no_changes(self, service, mock_repo):
        existing = {"pricing_id": "p1", "unit_price": 0.003}
        mock_repo.admin_get_pricing.return_value = existing
        result = await service.admin_update_pricing("p1", {})
        assert result == existing
        mock_repo.admin_update_pricing.assert_not_called()


# ============================================================================
# Cost Definition CRUD + Rotation
# ============================================================================

class TestAdminCostDefinitions:

    async def test_list_cost_definitions_delegates(self, service, mock_repo):
        mock_repo.get_cost_definitions.return_value = [{"cost_id": "c1"}]
        result = await service.admin_get_cost_definitions(is_active=True, provider="anthropic")
        assert len(result) == 1
        mock_repo.get_cost_definitions.assert_called_once_with(
            is_active=True, provider="anthropic", service_type=None
        )

    async def test_create_cost_definition_delegates(self, service, mock_repo):
        mock_repo.create_cost_definition.return_value = {"cost_id": "new"}
        result = await service.admin_create_cost_definition({
            "cost_id": "new", "service_type": "model_inference",
            "cost_per_unit": 300, "unit_type": "token",
        })
        assert result == {"cost_id": "new"}

    async def test_create_cost_definition_rejects_past_effective_from(self, service):
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="cannot be in the past"):
            await service.admin_create_cost_definition({
                "cost_id": "x", "service_type": "model_inference",
                "cost_per_unit": 100, "unit_type": "token",
                "effective_from": past,
            })

    async def test_update_cost_definition_returns_none_when_missing(self, service, mock_repo):
        mock_repo.get_cost_definition.return_value = None
        result = await service.admin_update_cost_definition("missing", {"description": "new"})
        assert result is None

    async def test_get_cost_history_delegates(self, service, mock_repo):
        mock_repo.get_cost_history.return_value = [{"cost_id": "c1"}, {"cost_id": "c2"}]
        result = await service.admin_get_cost_history("claude-sonnet-4-20250514")
        assert len(result) == 2


class TestAdminCostRotation:

    async def test_rotate_expires_old_and_creates_new(self, service, mock_repo):
        old_def = {
            "cost_id": "c1", "product_id": "p1", "service_type": "model_inference",
            "provider": "anthropic", "model_name": "claude-sonnet-4",
            "operation_type": "input", "cost_per_unit": 300,
            "unit_type": "token", "unit_size": 1000,
            "original_cost_usd": 0.003, "margin_percentage": 30.0,
            "free_tier_limit": 0, "free_tier_period": "monthly",
            "description": "Sonnet 4 input",
        }
        mock_repo.get_cost_definition.return_value = old_def
        mock_repo.create_cost_definition.return_value = {"cost_id": "c1_v_new"}

        future = (datetime.utcnow() + timedelta(days=1)).isoformat()
        results = await service.admin_rotate_cost_definitions([{
            "cost_id": "c1", "new_cost_per_unit": 400, "effective_from": future,
        }])

        assert len(results) == 1
        mock_repo.expire_cost_definition.assert_called_once()
        mock_repo.create_cost_definition.assert_called_once()
        created_data = mock_repo.create_cost_definition.call_args[0][0]
        assert created_data["cost_per_unit"] == 400

    async def test_rotate_raises_when_cost_not_found(self, service, mock_repo):
        mock_repo.get_cost_definition.return_value = None
        future = (datetime.utcnow() + timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="not found"):
            await service.admin_rotate_cost_definitions([{
                "cost_id": "missing", "effective_from": future,
            }])

    async def test_rotate_rejects_past_effective_from(self, service, mock_repo):
        mock_repo.get_cost_definition.return_value = {"cost_id": "c1", "service_type": "x"}
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="cannot be in the past"):
            await service.admin_rotate_cost_definitions([{
                "cost_id": "c1", "effective_from": past,
            }])


# ============================================================================
# Catalog Alignment
# ============================================================================

class TestCatalogAlignment:

    async def test_alignment_delegates_to_repository(self, service, mock_repo):
        mock_repo.get_catalog_alignment.return_value = {
            "aligned": True, "total_products": 6, "total_cost_definitions": 6,
            "products_without_cost_definitions": [],
            "cost_definitions_without_products": [],
        }
        result = await service.get_catalog_alignment()
        assert result["aligned"] is True
        mock_repo.get_catalog_alignment.assert_called_once()

    async def test_alignment_reports_mismatches(self, service, mock_repo):
        mock_repo.get_catalog_alignment.return_value = {
            "aligned": False, "total_products": 5, "total_cost_definitions": 6,
            "products_without_cost_definitions": [],
            "cost_definitions_without_products": [
                {"model_name": "new-model", "action": "Add product entry"}
            ],
        }
        result = await service.get_catalog_alignment()
        assert result["aligned"] is False
        assert len(result["cost_definitions_without_products"]) == 1


# ============================================================================
# Delegation (Subscription/Billing Clients)
# ============================================================================

class TestDelegationWiring:

    async def test_service_has_repository(self, service):
        assert service.repository is not None

    async def test_get_product_delegates_to_repo(self, service, mock_repo):
        mock_repo.get_product.return_value = make_mock_product()
        result = await service.get_product("test-model")
        assert result is not None
        mock_repo.get_product.assert_called_once_with("test-model")
