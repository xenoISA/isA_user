from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.billing_service.billing_service import BillingService
from microservices.billing_service.events import handlers as billing_handlers
from microservices.billing_service.models import (
    BillingCalculationResponse,
    BillingMethod,
    Currency,
    ProcessBillingRequest,
    ProcessBillingResponse,
    RecordUsageRequest,
    ServiceType,
)


class FakeClaimRepository:
    def __init__(self):
        self.claims = {}

    async def claim_event_processing(
        self,
        claim_key: str,
        source_event_id: str,
        processor_id: str,
        stale_after_seconds: int = 300,
    ) -> bool:
        claim = self.claims.get(claim_key)
        if claim and claim["status"] in {"processing", "completed"}:
            return False
        self.claims[claim_key] = {
            "status": "processing",
            "source_event_id": source_event_id,
            "processor_id": processor_id,
            "stale_after_seconds": stale_after_seconds,
        }
        return True

    async def mark_event_processing_completed(
        self,
        claim_key: str,
        source_event_id: str,
    ) -> None:
        self.claims[claim_key] = {
            "status": "completed",
            "source_event_id": source_event_id,
        }

    async def mark_event_processing_failed(
        self,
        claim_key: str,
        source_event_id: str,
        error_message: str,
    ) -> None:
        self.claims[claim_key] = {
            "status": "failed",
            "source_event_id": source_event_id,
            "error_message": error_message,
        }


def _make_event(
    *,
    event_id: str = "evt_001",
    handled: bool = False,
    idempotency_key: str | None = None,
):
    event = MagicMock()
    event.id = event_id
    event.data = {
        "user_id": "user_123",
        "actor_user_id": "user_123",
        "billing_account_type": "organization",
        "billing_account_id": "org_123",
        "organization_id": "org_123",
        "agent_id": "agent_123",
        "product_id": "gpt-4o-mini",
        "usage_amount": "42",
        "unit_type": "token",
        "billing_surface": "abstract_service",
        "cost_components": [
            {
                "component_id": "openai_model_provider",
                "component_type": "external_api",
                "provider": "openai",
            }
        ],
        "usage_details": {"service_type": "model_inference"},
        "timestamp": "2026-04-08T12:00:00",
        "credit_consumption_handled": handled,
        "idempotency_key": idempotency_key or f"idem:{event_id}",
        "credits_used": 84,
        "cost_usd": "0.0042",
    }
    return event


@pytest.fixture(autouse=True)
def clear_processed_event_ids():
    billing_handlers._processed_event_ids.clear()
    yield
    billing_handlers._processed_event_ids.clear()


@pytest.mark.unit
class TestUsageEventHandler:
    @pytest.mark.asyncio
    async def test_uses_external_billing_path_when_upstream_charge_exists(self):
        billing_service = AsyncMock()
        billing_service.record_usage_with_external_billing = AsyncMock(
            return_value=ProcessBillingResponse(
                success=True,
                message="ok",
                billing_record_id="bill_ext_123",
                amount_charged=Decimal("0.0042"),
                billing_method_used=BillingMethod.CREDIT_CONSUMPTION,
            )
        )
        billing_service.record_usage_and_bill = AsyncMock()
        event_bus = AsyncMock()

        await billing_handlers.handle_usage_recorded(
            _make_event(handled=True),
            billing_service,
            event_bus,
        )

        billing_service.record_usage_with_external_billing.assert_called_once()
        billing_service.record_usage_and_bill.assert_not_called()
        request_arg = billing_service.record_usage_with_external_billing.call_args.args[0]
        assert request_arg.product_id == "gpt-4o-mini"
        assert request_arg.service_type == ServiceType.MODEL_INFERENCE
        assert request_arg.actor_user_id == "user_123"
        assert request_arg.billing_account_type.value == "organization"
        assert request_arg.billing_account_id == "org_123"
        assert request_arg.agent_id == "agent_123"
        assert request_arg.billing_surface == "abstract_service"
        assert request_arg.cost_components == [
            {
                "component_id": "openai_model_provider",
                "component_type": "external_api",
                "bundled": True,
                "customer_visible": False,
                "provider": "openai",
            }
        ]
        assert request_arg.usage_details["cost_components"][0]["component_id"] == "openai_model_provider"
        assert billing_service.record_usage_with_external_billing.call_args.kwargs["credits_used"] == 84
        assert (
            billing_service.record_usage_with_external_billing.call_args.kwargs["cost_usd"]
            == Decimal("0.0042")
        )
        assert "evt_001" in billing_handlers._processed_event_ids
        assert "idem:evt_001" in billing_handlers._processed_event_ids

    @pytest.mark.asyncio
    async def test_uses_normal_billing_path_when_upstream_charge_not_handled(self):
        billing_service = AsyncMock()
        billing_service.record_usage_with_external_billing = AsyncMock()
        billing_service.record_usage_and_bill = AsyncMock(
            return_value=ProcessBillingResponse(
                success=True,
                message="ok",
                billing_record_id="bill_123",
                amount_charged=Decimal("1.23"),
                billing_method_used=BillingMethod.WALLET_DEDUCTION,
            )
        )
        event_bus = AsyncMock()

        await billing_handlers.handle_usage_recorded(
            _make_event(handled=False),
            billing_service,
            event_bus,
        )

        billing_service.record_usage_and_bill.assert_called_once()
        billing_service.record_usage_with_external_billing.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_idempotency_key_was_already_processed(self):
        billing_service = AsyncMock()
        event_bus = AsyncMock()
        billing_handlers.mark_event_processed("idem:evt_dup")

        await billing_handlers.handle_usage_recorded(
            _make_event(event_id="evt_dup", handled=True),
            billing_service,
            event_bus,
        )

        billing_service.record_usage_with_external_billing.assert_not_called()
        billing_service.record_usage_and_bill.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_durable_claims_to_skip_duplicate_redelivery(self):
        billing_service = AsyncMock()
        billing_service.repository = FakeClaimRepository()
        billing_service.record_usage_with_external_billing = AsyncMock(
            return_value=ProcessBillingResponse(
                success=True,
                message="ok",
                billing_record_id="bill_ext_123",
                amount_charged=Decimal("0.0042"),
                billing_method_used=BillingMethod.CREDIT_CONSUMPTION,
            )
        )
        billing_service.record_usage_and_bill = AsyncMock()
        event_bus = AsyncMock()

        await billing_handlers.handle_usage_recorded(
            _make_event(
                event_id="evt_durable",
                handled=True,
                idempotency_key="idem:durable-shared",
            ),
            billing_service,
            event_bus,
        )
        await billing_handlers.handle_usage_recorded(
            _make_event(
                event_id="evt_durable_retry",
                handled=True,
                idempotency_key="idem:durable-shared",
            ),
            billing_service,
            event_bus,
        )

        billing_service.record_usage_with_external_billing.assert_called_once()
        assert (
            billing_service.repository.claims["idem:durable-shared"]["status"]
            == "completed"
        )

    @pytest.mark.asyncio
    async def test_failed_claim_can_be_retried_after_failure(self):
        billing_service = AsyncMock()
        billing_service.repository = FakeClaimRepository()
        billing_service.record_usage_with_external_billing = AsyncMock(
            side_effect=[
                RuntimeError("temporary failure"),
                ProcessBillingResponse(
                    success=True,
                    message="ok",
                    billing_record_id="bill_ext_456",
                    amount_charged=Decimal("0.0042"),
                    billing_method_used=BillingMethod.CREDIT_CONSUMPTION,
                ),
            ]
        )
        billing_service.record_usage_and_bill = AsyncMock()
        event_bus = AsyncMock()

        await billing_handlers.handle_usage_recorded(
            _make_event(
                event_id="evt_retryable",
                handled=True,
                idempotency_key="idem:retryable-shared",
            ),
            billing_service,
            event_bus,
        )
        assert (
            billing_service.repository.claims["idem:retryable-shared"]["status"]
            == "failed"
        )

        await billing_handlers.handle_usage_recorded(
            _make_event(
                event_id="evt_retryable_second",
                handled=True,
                idempotency_key="idem:retryable-shared",
            ),
            billing_service,
            event_bus,
        )

        assert billing_service.record_usage_with_external_billing.call_count == 2
        assert (
            billing_service.repository.claims["idem:retryable-shared"]["status"]
            == "completed"
        )


@pytest.mark.unit
class TestBillingServiceExternalBilling:
    @pytest.mark.asyncio
    async def test_records_external_billing_without_consuming_credits(self):
        repository = AsyncMock()
        repository.create_billing_record = AsyncMock(side_effect=lambda record: record)
        repository.create_billing_event = AsyncMock(side_effect=lambda event: event)
        event_bus = AsyncMock()
        subscription_client = AsyncMock()

        service = BillingService(
            repository=repository,
            event_bus=event_bus,
            product_client=AsyncMock(),
            wallet_client=AsyncMock(),
            subscription_client=subscription_client,
        )
        service._record_usage_to_product_service = AsyncMock(return_value="usage_123")
        service.calculate_billing_cost = AsyncMock(
            return_value=BillingCalculationResponse(
                success=True,
                message="ok",
                user_id="user_123",
                organization_id="org_123",
                agent_id="agent_123",
                subscription_id="sub_123",
                product_id="gpt-4o-mini",
                usage_amount=Decimal("42"),
                unit_price=Decimal("0.0292857143"),
                total_cost=Decimal("1.23"),
                currency=Currency.USD,
                suggested_billing_method=BillingMethod.CREDIT_CONSUMPTION,
                available_billing_methods=[BillingMethod.CREDIT_CONSUMPTION],
            )
        )

        result = await service.record_usage_with_external_billing(
            RecordUsageRequest(
                user_id="user_123",
                organization_id="org_123",
                agent_id="agent_123",
                subscription_id="sub_123",
                product_id="gpt-4o-mini",
                service_type=ServiceType.MODEL_INFERENCE,
                usage_amount=Decimal("42"),
                usage_details={"service_type": "model_inference"},
            ),
            credits_used=84,
            cost_usd=Decimal("0.0042"),
            idempotency_key="idem:evt_123",
            source_event_id="evt_123",
        )

        assert result.success is True
        assert result.billing_method_used == BillingMethod.CREDIT_CONSUMPTION
        subscription_client.consume_credits.assert_not_called()
        record = repository.create_billing_record.call_args.args[0]
        assert record.service_type == ServiceType.MODEL_INFERENCE
        assert record.agent_id == "agent_123"
        assert record.actor_user_id == "user_123"
        assert record.billing_account_type.value == "organization"
        assert record.billing_account_id == "org_123"
        assert record.billing_metadata["charged_upstream"] is True
        assert record.billing_metadata["credit_consumption_handled"] is True
        assert record.billing_metadata["upstream_credits_used"] == 84
        assert record.billing_metadata["upstream_cost_usd"] == "0.0042"
        assert record.total_amount == Decimal("0.0042")
        assert record.unit_price == Decimal("0.0001")

    @pytest.mark.asyncio
    async def test_record_usage_and_bill_passes_canonical_context_to_process_billing(self):
        repository = AsyncMock()
        service = BillingService(
            repository=repository,
            event_bus=AsyncMock(),
            product_client=AsyncMock(),
            wallet_client=AsyncMock(),
            subscription_client=AsyncMock(),
        )
        service._record_usage_to_product_service = AsyncMock(return_value="usage_123")
        service.calculate_billing_cost = AsyncMock(
            return_value=BillingCalculationResponse(
                success=True,
                message="ok",
                user_id="user_123",
                actor_user_id="user_123",
                billing_account_type="organization",
                billing_account_id="org_123",
                organization_id="org_123",
                agent_id="agent_123",
                subscription_id="sub_123",
                product_id="web_search",
                usage_amount=Decimal("3"),
                unit_price=Decimal("1"),
                total_cost=Decimal("3"),
                currency=Currency.CREDIT,
                suggested_billing_method=BillingMethod.CREDIT_CONSUMPTION,
                available_billing_methods=[BillingMethod.CREDIT_CONSUMPTION],
            )
        )
        service.check_quota = AsyncMock(return_value=MagicMock(allowed=True))
        service.process_billing = AsyncMock(
            return_value=ProcessBillingResponse(
                success=True,
                message="processed",
                billing_record_id="bill_123",
                amount_charged=Decimal("3"),
                billing_method_used=BillingMethod.CREDIT_CONSUMPTION,
            )
        )

        result = await service.record_usage_and_bill(
            RecordUsageRequest(
                user_id="user_123",
                actor_user_id="user_123",
                billing_account_type="organization",
                billing_account_id="org_123",
                organization_id="org_123",
                agent_id="agent_123",
                subscription_id="sub_123",
                product_id="web_search",
                service_type=ServiceType.WEB_SERVICE,
                usage_amount=Decimal("3"),
                unit_type="request",
                meter_type="tool_calls",
                operation_type="search",
                source_service="web_service",
                resource_name="web_search",
                billing_surface="abstract_service",
                cost_components=[
                    {
                        "component_id": "browser_api",
                        "component_type": "external_api",
                    }
                ],
                usage_details={"scenario_id": "web_search_internal_org"},
            )
        )

        assert result.success is True
        process_request = service.process_billing.call_args.args[0]
        assert process_request.actor_user_id == "user_123"
        assert process_request.billing_account_type.value == "organization"
        assert process_request.billing_account_id == "org_123"
        assert process_request.organization_id == "org_123"
        assert process_request.agent_id == "agent_123"
        assert process_request.subscription_id == "sub_123"
        assert process_request.billing_metadata["charged_upstream"] is False
        assert process_request.billing_metadata["credit_consumption_handled"] is False
        assert (
            process_request.billing_metadata["usage_details"]["scenario_id"]
            == "web_search_internal_org"
        )

    @pytest.mark.asyncio
    async def test_process_billing_persists_request_context_for_internal_billing(self):
        repository = AsyncMock()
        repository.create_billing_record = AsyncMock(side_effect=lambda record: record)
        repository.update_billing_record_status = AsyncMock(side_effect=lambda *args, **kwargs: None)
        repository.create_billing_event = AsyncMock(side_effect=lambda event: event)
        service = BillingService(
            repository=repository,
            event_bus=AsyncMock(),
            product_client=AsyncMock(),
            wallet_client=AsyncMock(),
            subscription_client=AsyncMock(),
        )
        service._process_purchased_credit_consumption = AsyncMock(
            return_value=(True, "txn_123", None)
        )

        result = await service.process_billing(
            ProcessBillingRequest(
                usage_record_id="usage_123",
                billing_method=BillingMethod.CREDIT_CONSUMPTION,
                service_type=ServiceType.WEB_SERVICE,
                actor_user_id="user_123",
                billing_account_type="organization",
                billing_account_id="org_123",
                organization_id="org_123",
                agent_id="agent_123",
                subscription_id="sub_123",
                billing_metadata={
                    "charged_upstream": False,
                    "credit_consumption_handled": False,
                    "usage_details": {"scenario_id": "web_search_internal_org"},
                },
            ),
            BillingCalculationResponse(
                success=True,
                message="ok",
                user_id="user_123",
                product_id="web_search",
                usage_amount=Decimal("3"),
                unit_price=Decimal("1"),
                total_cost=Decimal("3"),
                currency=Currency.CREDIT,
                suggested_billing_method=BillingMethod.CREDIT_CONSUMPTION,
                available_billing_methods=[BillingMethod.CREDIT_CONSUMPTION],
            ),
        )

        assert result.success is True
        record = repository.create_billing_record.call_args.args[0]
        assert record.actor_user_id == "user_123"
        assert record.billing_account_type.value == "organization"
        assert record.billing_account_id == "org_123"
        assert record.organization_id == "org_123"
        assert record.agent_id == "agent_123"
        assert record.subscription_id == "sub_123"
        assert record.billing_metadata["charged_upstream"] is False
        assert record.billing_metadata["credit_consumption_handled"] is False
        assert (
            record.billing_metadata["usage_details"]["scenario_id"]
            == "web_search_internal_org"
        )
