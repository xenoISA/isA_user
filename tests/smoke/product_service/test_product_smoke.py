import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase, internal_headers

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestProductSmoke(CrudApiSmokeBase):
    service_name = "product_service"
    env_var_name = "PRODUCT_BASE_URL"
    create_path = "/api/v1/product/admin/products"
    list_path = "/api/v1/product/products"
    get_path = "/api/v1/product/products/{product_id}"
    update_path = "/api/v1/product/admin/products/{product_id}"
    delete_path = "/api/v1/product/admin/products/{product_id}"
    create_success_statuses = (201,)
    id_keys = ("product_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "product_id": f"prod_smoke_{suffix}",
            "product_name": f"Smoke Product {suffix}",
            "product_code": f"SMOKE_{suffix.upper()}",
            "description": "Product created by smoke test",
            "category": "ai_models",
            "product_type": "api_service",
            "base_price": 0.05,
            "currency": "USD",
            "billing_interval": "monthly",
            "features": ["smoke"],
            "quota_limits": {"requests_per_day": 100},
            "metadata": {"smoke": True},
            "tags": ["smoke"],
            "is_active": True,
        }

    def request_headers(self, state: dict) -> dict[str, str]:
        headers = internal_headers("product_admin_smoke")
        headers["X-Admin-Role"] = "true"
        headers["X-Admin-User-Id"] = "product_admin_smoke"
        headers["X-Admin-Email"] = "product_admin_smoke@example.com"
        return headers

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "product_name": f"Updated Smoke Product {suffix}",
            "description": "Updated by smoke test",
            "base_price": 0.08,
        }
