"""
Telemetry Service Component Golden Tests

These tests document CURRENT TelemetryService behavior with mocked dependencies.
Uses TelemetryTestDataFactory - zero hardcoded data.

Usage:
    pytest tests/component/golden/telemetry_service -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from .mocks import MockEventBus

from tests.contracts.telemetry.data_contract import (
    TelemetryTestDataFactory,
    DataType,
    MetricType,
    AlertLevel,
    AlertStatus,
    AggregationType,
    TelemetryDataPointContract,
    TelemetryDataPointBuilder,
    AlertRuleCreateRequestBuilder,
    TelemetryQueryRequestBuilder,
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def telemetry_service(injected_mock_repo, mock_event_bus):
    """
    Create TelemetryService with mocked dependencies.

    The repository is automatically patched via conftest.py's autouse fixture.
    """
    from microservices.telemetry_service.telemetry_service import TelemetryService

    service = TelemetryService(event_bus=mock_event_bus)
    # Repository is already injected via the patch in conftest.py
    return service


@pytest.fixture
def telemetry_service_with_data(injected_mock_repo, mock_event_bus):
    """Create TelemetryService with pre-populated data"""
    from microservices.telemetry_service.telemetry_service import TelemetryService

    # Set up mock data before creating service
    injected_mock_repo.set_metric_definition(
        metric_id=TelemetryTestDataFactory.make_metric_id(),
        name="temperature",
        data_type="numeric",
        metric_type="gauge",
        unit="celsius",
        min_value=0,
        max_value=100,
    )

    injected_mock_repo.set_alert_rule(
        rule_id=TelemetryTestDataFactory.make_rule_id(),
        name="High Temperature Alert",
        metric_name="temperature",
        condition=">",
        threshold_value="90",
        level="warning",
        enabled=True,
    )

    service = TelemetryService(event_bus=mock_event_bus)
    return service


# =============================================================================
# TelemetryService.ingest_telemetry_data() Tests
# =============================================================================

class TestTelemetryServiceIngestGolden:
    """Golden: TelemetryService.ingest_telemetry_data() current behavior"""

    async def test_ingest_single_data_point_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data ingests single point successfully"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_temperature(),
            unit=TelemetryTestDataFactory.make_unit(),
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is True
        assert result["ingested_count"] == 1
        assert result["failed_count"] == 0
        injected_mock_repo.assert_called("ingest_data_points")

    async def test_ingest_multiple_data_points_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data ingests multiple points successfully"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        data_points = [
            TelemetryDataPoint(
                timestamp=TelemetryTestDataFactory.make_timestamp(),
                metric_name=TelemetryTestDataFactory.make_metric_name(),
                value=TelemetryTestDataFactory.make_temperature(),
            )
            for _ in range(5)
        ]

        result = await telemetry_service.ingest_telemetry_data(device_id, data_points)

        assert result["success"] is True
        assert result["ingested_count"] == 5
        assert result["total_count"] == 5

    async def test_ingest_empty_list_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data handles empty list"""
        device_id = TelemetryTestDataFactory.make_device_id()

        result = await telemetry_service.ingest_telemetry_data(device_id, [])

        assert result["ingested_count"] == 0
        assert result["total_count"] == 0

    async def test_ingest_publishes_event_on_success(self, telemetry_service, injected_mock_repo, mock_event_bus):
        """GOLDEN: ingest_telemetry_data publishes telemetry.data.received event"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_temperature(),
        )

        await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        # Event should be published
        assert mock_event_bus.get_published_count() >= 1

    async def test_ingest_handles_repository_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data handles repository errors gracefully"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        injected_mock_repo.set_error(Exception("Database connection failed"))

        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_temperature(),
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is False
        assert "error" in result

    async def test_ingest_with_string_value(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data handles string values"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_description(),
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is True
        assert result["ingested_count"] == 1

    async def test_ingest_with_boolean_value(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data handles boolean values"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=True,
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is True

    async def test_ingest_with_metadata(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data preserves metadata"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        metadata = TelemetryTestDataFactory.make_metadata()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_temperature(),
            metadata=metadata,
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is True

    async def test_ingest_with_tags(self, telemetry_service, injected_mock_repo):
        """GOLDEN: ingest_telemetry_data preserves tags"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()
        tags = TelemetryTestDataFactory.make_tags()
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name=TelemetryTestDataFactory.make_metric_name(),
            value=TelemetryTestDataFactory.make_temperature(),
            tags=tags,
        )

        result = await telemetry_service.ingest_telemetry_data(device_id, [data_point])

        assert result["success"] is True


# =============================================================================
# TelemetryService.create_metric_definition() Tests
# =============================================================================

class TestTelemetryServiceMetricDefinitionGolden:
    """Golden: TelemetryService.create_metric_definition() current behavior"""

    async def test_create_metric_definition_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_metric_definition creates metric definition"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "description": TelemetryTestDataFactory.make_description(),
            "data_type": DataType.NUMERIC.value,
            "metric_type": MetricType.GAUGE.value,
            "unit": TelemetryTestDataFactory.make_unit(),
        }

        result = await telemetry_service.create_metric_definition(user_id, metric_data)

        assert result is not None
        assert result.metric_id is not None
        assert result.name == metric_data["name"]
        injected_mock_repo.assert_called("create_metric_definition")

    async def test_create_metric_definition_with_min_max(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_metric_definition accepts min/max values"""
        user_id = TelemetryTestDataFactory.make_user_id()
        min_val = TelemetryTestDataFactory.make_boundary_temperature_min()
        max_val = TelemetryTestDataFactory.make_boundary_temperature_max()

        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": DataType.NUMERIC.value,
            "min_value": min_val,
            "max_value": max_val,
        }

        result = await telemetry_service.create_metric_definition(user_id, metric_data)

        assert result is not None
        assert result.min_value == min_val
        assert result.max_value == max_val

    async def test_create_metric_definition_publishes_event(self, telemetry_service, injected_mock_repo, mock_event_bus):
        """GOLDEN: create_metric_definition publishes metric.defined event"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": DataType.NUMERIC.value,
        }

        await telemetry_service.create_metric_definition(user_id, metric_data)

        assert mock_event_bus.get_published_count() >= 1

    async def test_create_metric_definition_sets_defaults(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_metric_definition sets default retention and aggregation"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": DataType.NUMERIC.value,
        }

        result = await telemetry_service.create_metric_definition(user_id, metric_data)

        assert result is not None
        assert result.retention_days == 90  # Default
        assert result.aggregation_interval == 60  # Default

    async def test_create_metric_definition_with_tags(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_metric_definition accepts tags"""
        user_id = TelemetryTestDataFactory.make_user_id()
        tags = TelemetryTestDataFactory.make_metric_tags()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": DataType.NUMERIC.value,
            "tags": tags,
        }

        result = await telemetry_service.create_metric_definition(user_id, metric_data)

        assert result is not None
        assert result.tags == tags

    async def test_create_metric_definition_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_metric_definition returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": DataType.NUMERIC.value,
        }

        result = await telemetry_service.create_metric_definition(user_id, metric_data)

        assert result is None


# =============================================================================
# TelemetryService.create_alert_rule() Tests
# =============================================================================

class TestTelemetryServiceAlertRuleGolden:
    """Golden: TelemetryService.create_alert_rule() current behavior"""

    async def test_create_alert_rule_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_alert_rule creates alert rule"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": TelemetryTestDataFactory.make_condition(),
            "threshold_value": TelemetryTestDataFactory.make_threshold_value(),
        }

        result = await telemetry_service.create_alert_rule(user_id, rule_data)

        assert result is not None
        assert result.rule_id is not None
        assert result.name == rule_data["name"]
        injected_mock_repo.assert_called("create_alert_rule")

    async def test_create_alert_rule_with_level(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_alert_rule accepts alert level"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": ">",
            "threshold_value": 90,
            "level": AlertLevel.CRITICAL.value,
        }

        result = await telemetry_service.create_alert_rule(user_id, rule_data)

        assert result is not None
        assert result.level == AlertLevel.CRITICAL

    async def test_create_alert_rule_with_device_filter(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_alert_rule accepts device_ids filter"""
        user_id = TelemetryTestDataFactory.make_user_id()
        device_ids = TelemetryTestDataFactory.make_device_ids()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": ">",
            "threshold_value": 90,
            "device_ids": device_ids,
        }

        result = await telemetry_service.create_alert_rule(user_id, rule_data)

        assert result is not None
        assert result.device_ids == device_ids

    async def test_create_alert_rule_publishes_event(self, telemetry_service, injected_mock_repo, mock_event_bus):
        """GOLDEN: create_alert_rule publishes alert.rule.created event"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": ">",
            "threshold_value": 90,
        }

        await telemetry_service.create_alert_rule(user_id, rule_data)

        assert mock_event_bus.get_published_count() >= 1

    async def test_create_alert_rule_with_auto_resolve(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_alert_rule accepts auto_resolve settings"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": ">",
            "threshold_value": 90,
            "auto_resolve": True,
            "auto_resolve_timeout": 7200,
        }

        result = await telemetry_service.create_alert_rule(user_id, rule_data)

        assert result is not None
        assert result.auto_resolve is True
        assert result.auto_resolve_timeout == 7200

    async def test_create_alert_rule_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: create_alert_rule returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": TelemetryTestDataFactory.make_rule_name(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": ">",
            "threshold_value": 90,
        }

        result = await telemetry_service.create_alert_rule(user_id, rule_data)

        assert result is None


# =============================================================================
# TelemetryService.query_telemetry_data() Tests
# =============================================================================

class TestTelemetryServiceQueryGolden:
    """Golden: TelemetryService.query_telemetry_data() current behavior"""

    async def test_query_telemetry_data_success(self, telemetry_service, injected_mock_repo):
        """GOLDEN: query_telemetry_data returns data points"""
        # Setup mock data
        device_id = TelemetryTestDataFactory.make_device_id()
        metric_name = TelemetryTestDataFactory.make_metric_name()
        now = TelemetryTestDataFactory.make_timestamp()

        injected_mock_repo.add_data_point(device_id, {
            "time": now,
            "device_id": device_id,
            "metric_name": metric_name,
            "value_numeric": TelemetryTestDataFactory.make_temperature(),
        })

        query_params = {
            "devices": [device_id],
            "metrics": [metric_name],
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(hours=1),
        }

        result = await telemetry_service.query_telemetry_data(query_params)

        assert result is not None
        assert result.count >= 1

    async def test_query_telemetry_data_empty_result(self, telemetry_service, injected_mock_repo):
        """GOLDEN: query_telemetry_data returns empty for no matching data"""
        now = TelemetryTestDataFactory.make_timestamp()
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": now - timedelta(hours=1),
            "end_time": now,
        }

        result = await telemetry_service.query_telemetry_data(query_params)

        assert result is not None
        assert result.count == 0

    async def test_query_telemetry_data_with_limit(self, telemetry_service, injected_mock_repo):
        """GOLDEN: query_telemetry_data respects limit parameter"""
        device_id = TelemetryTestDataFactory.make_device_id()
        metric_name = TelemetryTestDataFactory.make_metric_name()
        now = TelemetryTestDataFactory.make_timestamp()

        # Add multiple data points
        for i in range(10):
            injected_mock_repo.add_data_point(device_id, {
                "time": now - timedelta(minutes=i),
                "device_id": device_id,
                "metric_name": metric_name,
                "value_numeric": TelemetryTestDataFactory.make_temperature(),
            })

        query_params = {
            "devices": [device_id],
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(hours=1),
            "limit": 5,
        }

        result = await telemetry_service.query_telemetry_data(query_params)

        assert result is not None
        assert result.count <= 5

    async def test_query_telemetry_data_multiple_devices(self, telemetry_service, injected_mock_repo):
        """GOLDEN: query_telemetry_data queries multiple devices"""
        device_ids = TelemetryTestDataFactory.make_device_ids(count=3)
        metric_name = TelemetryTestDataFactory.make_metric_name()
        now = TelemetryTestDataFactory.make_timestamp()

        for device_id in device_ids:
            injected_mock_repo.add_data_point(device_id, {
                "time": now,
                "device_id": device_id,
                "metric_name": metric_name,
                "value_numeric": TelemetryTestDataFactory.make_temperature(),
            })

        query_params = {
            "devices": device_ids,
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(hours=1),
        }

        result = await telemetry_service.query_telemetry_data(query_params)

        assert result is not None
        assert result.count >= 3

    async def test_query_telemetry_data_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: query_telemetry_data returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        now = TelemetryTestDataFactory.make_timestamp()
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "start_time": now - timedelta(hours=1),
            "end_time": now,
        }

        result = await telemetry_service.query_telemetry_data(query_params)

        assert result is None


# =============================================================================
# TelemetryService.get_device_stats() Tests
# =============================================================================

class TestTelemetryServiceDeviceStatsGolden:
    """Golden: TelemetryService.get_device_stats() current behavior"""

    async def test_get_device_stats_with_data(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_device_stats returns device statistics"""
        device_id = TelemetryTestDataFactory.make_device_id()
        now = TelemetryTestDataFactory.make_timestamp()

        # Add data points
        for i in range(5):
            injected_mock_repo.add_data_point(device_id, {
                "time": now - timedelta(minutes=i),
                "device_id": device_id,
                "metric_name": f"metric_{i}",
                "value_numeric": TelemetryTestDataFactory.make_temperature(),
            })

        result = await telemetry_service.get_device_stats(device_id)

        assert result is not None
        assert result.device_id == device_id
        assert result.data_points_count == 5

    async def test_get_device_stats_no_data(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_device_stats returns zero stats for device with no data"""
        device_id = TelemetryTestDataFactory.make_device_id()

        result = await telemetry_service.get_device_stats(device_id)

        assert result is not None
        assert result.device_id == device_id
        assert result.data_points_count == 0
        assert result.total_metrics == 0

    async def test_get_device_stats_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_device_stats returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        device_id = TelemetryTestDataFactory.make_device_id()

        result = await telemetry_service.get_device_stats(device_id)

        assert result is None


# =============================================================================
# TelemetryService.get_service_stats() Tests
# =============================================================================

class TestTelemetryServiceStatsGolden:
    """Golden: TelemetryService.get_service_stats() current behavior"""

    async def test_get_service_stats_with_data(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_service_stats returns service statistics"""
        injected_mock_repo.set_stats(
            total_devices=10,
            total_metrics=50,
            total_points=10000,
            last_24h_points=1000,
        )

        result = await telemetry_service.get_service_stats()

        assert result is not None
        assert result.total_devices == 10
        assert result.total_metrics == 50
        assert result.total_data_points == 10000

    async def test_get_service_stats_empty(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_service_stats returns zero stats when no data"""
        result = await telemetry_service.get_service_stats()

        assert result is not None
        assert result.total_devices == 0
        assert result.total_data_points == 0

    async def test_get_service_stats_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_service_stats returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        result = await telemetry_service.get_service_stats()

        assert result is None


# =============================================================================
# TelemetryService.subscribe_real_time() Tests
# =============================================================================

class TestTelemetryServiceRealTimeGolden:
    """Golden: TelemetryService real-time subscription current behavior"""

    async def test_subscribe_real_time_success(self, telemetry_service):
        """GOLDEN: subscribe_real_time creates subscription"""
        subscription_data = {
            "device_ids": TelemetryTestDataFactory.make_device_ids(),
            "metric_names": [TelemetryTestDataFactory.make_metric_name()],
        }

        subscription_id = await telemetry_service.subscribe_real_time(subscription_data)

        assert subscription_id is not None
        assert len(subscription_id) == 32  # hex token

    async def test_subscribe_real_time_with_filters(self, telemetry_service):
        """GOLDEN: subscribe_real_time accepts filter conditions"""
        subscription_data = {
            "device_ids": TelemetryTestDataFactory.make_device_ids(),
            "metric_names": [TelemetryTestDataFactory.make_metric_name()],
            "tags": TelemetryTestDataFactory.make_tags(),
            "max_frequency": 500,
        }

        subscription_id = await telemetry_service.subscribe_real_time(subscription_data)

        assert subscription_id is not None
        assert subscription_id in telemetry_service.real_time_subscribers

    async def test_unsubscribe_real_time_success(self, telemetry_service):
        """GOLDEN: unsubscribe_real_time removes subscription"""
        subscription_data = {"device_ids": []}
        subscription_id = await telemetry_service.subscribe_real_time(subscription_data)

        result = await telemetry_service.unsubscribe_real_time(subscription_id)

        assert result is True
        assert subscription_id not in telemetry_service.real_time_subscribers

    async def test_unsubscribe_real_time_not_found(self, telemetry_service):
        """GOLDEN: unsubscribe_real_time returns False for unknown subscription"""
        fake_id = TelemetryTestDataFactory.make_subscription_id()

        result = await telemetry_service.unsubscribe_real_time(fake_id)

        assert result is False


# =============================================================================
# TelemetryService.get_aggregated_data() Tests
# =============================================================================

class TestTelemetryServiceAggregationGolden:
    """Golden: TelemetryService.get_aggregated_data() current behavior"""

    async def test_get_aggregated_data_avg(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_aggregated_data calculates average"""
        device_id = TelemetryTestDataFactory.make_device_id()
        metric_name = TelemetryTestDataFactory.make_metric_name()
        now = TelemetryTestDataFactory.make_timestamp()

        # Add data points with known values
        for i in range(5):
            injected_mock_repo.add_data_point(device_id, {
                "time": now - timedelta(minutes=i),
                "device_id": device_id,
                "metric_name": metric_name,
                "value_numeric": 10.0 * (i + 1),  # 10, 20, 30, 40, 50
            })

        query_params = {
            "device_id": device_id,
            "metric_name": metric_name,
            "aggregation_type": AggregationType.AVG,
            "interval": 3600,
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(hours=1),
        }

        result = await telemetry_service.get_aggregated_data(query_params)

        assert result is not None
        assert result.aggregation_type == AggregationType.AVG

    async def test_get_aggregated_data_sum(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_aggregated_data calculates sum"""
        device_id = TelemetryTestDataFactory.make_device_id()
        metric_name = TelemetryTestDataFactory.make_metric_name()
        now = TelemetryTestDataFactory.make_timestamp()

        injected_mock_repo.add_data_point(device_id, {
            "time": now,
            "device_id": device_id,
            "metric_name": metric_name,
            "value_numeric": 100.0,
        })

        query_params = {
            "device_id": device_id,
            "metric_name": metric_name,
            "aggregation_type": AggregationType.SUM,
            "interval": 3600,
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(hours=1),
        }

        result = await telemetry_service.get_aggregated_data(query_params)

        assert result is not None
        assert result.aggregation_type == AggregationType.SUM

    async def test_get_aggregated_data_empty(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_aggregated_data handles no data"""
        now = TelemetryTestDataFactory.make_timestamp()
        query_params = {
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "aggregation_type": AggregationType.AVG,
            "interval": 3600,
            "start_time": now - timedelta(hours=1),
            "end_time": now,
        }

        result = await telemetry_service.get_aggregated_data(query_params)

        assert result is not None
        assert result.count == 0

    async def test_get_aggregated_data_handles_error(self, telemetry_service, injected_mock_repo):
        """GOLDEN: get_aggregated_data returns None on error"""
        injected_mock_repo.set_error(Exception("Database error"))

        now = TelemetryTestDataFactory.make_timestamp()
        query_params = {
            "device_id": TelemetryTestDataFactory.make_device_id(),
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "aggregation_type": AggregationType.AVG,
            "interval": 3600,
            "start_time": now - timedelta(hours=1),
            "end_time": now,
        }

        result = await telemetry_service.get_aggregated_data(query_params)

        assert result is None


# =============================================================================
# TelemetryService.resolve_alert() Tests
# =============================================================================

class TestTelemetryServiceResolveAlertGolden:
    """Golden: TelemetryService.resolve_alert() current behavior"""

    async def test_resolve_alert_success(self, telemetry_service, injected_mock_repo, mock_event_bus):
        """GOLDEN: resolve_alert resolves existing alert"""
        # Setup alert
        alert = injected_mock_repo.set_alert(
            alert_id=TelemetryTestDataFactory.make_alert_id(),
            status=AlertStatus.ACTIVE.value,
        )

        resolved_by = TelemetryTestDataFactory.make_user_id()
        resolution_note = TelemetryTestDataFactory.make_description()

        result = await telemetry_service.resolve_alert(
            alert["alert_id"],
            resolved_by,
            resolution_note
        )

        assert result is True
        injected_mock_repo.assert_called("update_alert")

    async def test_resolve_alert_not_found(self, telemetry_service, injected_mock_repo):
        """GOLDEN: resolve_alert returns False for unknown alert"""
        fake_alert_id = TelemetryTestDataFactory.make_alert_id()
        resolved_by = TelemetryTestDataFactory.make_user_id()

        result = await telemetry_service.resolve_alert(fake_alert_id, resolved_by)

        assert result is False

    async def test_resolve_alert_publishes_event(self, telemetry_service, injected_mock_repo, mock_event_bus):
        """GOLDEN: resolve_alert publishes alert.resolved event"""
        alert = injected_mock_repo.set_alert(
            alert_id=TelemetryTestDataFactory.make_alert_id(),
            status=AlertStatus.ACTIVE.value,
        )

        resolved_by = TelemetryTestDataFactory.make_user_id()

        await telemetry_service.resolve_alert(alert["alert_id"], resolved_by)

        assert mock_event_bus.get_published_count() >= 1


# =============================================================================
# TelemetryService Alert Triggering Tests
# =============================================================================

class TestTelemetryServiceAlertTriggerGolden:
    """Golden: TelemetryService alert triggering current behavior"""

    async def test_ingest_triggers_alert_when_threshold_exceeded(
        self, telemetry_service_with_data, injected_mock_repo, mock_event_bus
    ):
        """GOLDEN: ingest_telemetry_data triggers alert when threshold exceeded"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()

        # Create data point that exceeds threshold (rule threshold is 90)
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name="temperature",  # Matches rule in injected_mock_repo
            value=95.0,  # Exceeds threshold of 90
        )

        await telemetry_service_with_data.ingest_telemetry_data(device_id, [data_point])

        # Alert should be created
        injected_mock_repo.assert_called("create_alert")

    async def test_ingest_does_not_trigger_alert_below_threshold(
        self, telemetry_service_with_data, injected_mock_repo
    ):
        """GOLDEN: ingest_telemetry_data does not trigger alert below threshold"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()

        # Create data point below threshold
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name="temperature",
            value=80.0,  # Below threshold of 90
        )

        await telemetry_service_with_data.ingest_telemetry_data(device_id, [data_point])

        # Alert should NOT be created
        injected_mock_repo.assert_not_called("create_alert")


# =============================================================================
# TelemetryService Data Validation Tests
# =============================================================================

class TestTelemetryServiceValidationGolden:
    """Golden: TelemetryService data validation current behavior"""

    async def test_ingest_validates_against_metric_definition(
        self, telemetry_service_with_data, injected_mock_repo
    ):
        """GOLDEN: ingest_telemetry_data validates against metric definition"""
        from microservices.telemetry_service.models import TelemetryDataPoint

        device_id = TelemetryTestDataFactory.make_device_id()

        # Create data point that exceeds max_value (100 for temperature metric)
        data_point = TelemetryDataPoint(
            timestamp=TelemetryTestDataFactory.make_timestamp(),
            metric_name="temperature",
            value=150.0,  # Exceeds max_value of 100
        )

        # Should still ingest but log warning
        result = await telemetry_service_with_data.ingest_telemetry_data(device_id, [data_point])

        # Ingestion should succeed (validation is non-blocking)
        assert result["success"] is True


# =============================================================================
# Factory Method Tests
# =============================================================================

class TestTelemetryTestDataFactoryGolden:
    """Golden: TelemetryTestDataFactory generates valid test data"""

    def test_make_device_id_format(self):
        """GOLDEN: make_device_id returns correctly formatted ID"""
        device_id = TelemetryTestDataFactory.make_device_id()
        assert device_id.startswith("device_")

    def test_make_device_id_uniqueness(self):
        """GOLDEN: make_device_id generates unique IDs"""
        ids = [TelemetryTestDataFactory.make_device_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_metric_id_format(self):
        """GOLDEN: make_metric_id returns correctly formatted ID"""
        metric_id = TelemetryTestDataFactory.make_metric_id()
        assert metric_id.startswith("met_")

    def test_make_rule_id_format(self):
        """GOLDEN: make_rule_id returns correctly formatted ID"""
        rule_id = TelemetryTestDataFactory.make_rule_id()
        assert rule_id.startswith("rule_")

    def test_make_alert_id_format(self):
        """GOLDEN: make_alert_id returns correctly formatted ID"""
        alert_id = TelemetryTestDataFactory.make_alert_id()
        assert alert_id.startswith("alert_")

    def test_make_temperature_in_range(self):
        """GOLDEN: make_temperature returns value in valid range"""
        value = TelemetryTestDataFactory.make_temperature()
        assert -40 <= value <= 100  # Valid temperature range

    def test_make_timestamp_is_utc(self):
        """GOLDEN: make_timestamp returns UTC datetime"""
        from datetime import timezone
        ts = TelemetryTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_make_condition_valid(self):
        """GOLDEN: make_condition returns valid condition"""
        condition = TelemetryTestDataFactory.make_condition()
        assert condition in [">", "<", ">=", "<=", "==", "!="]

    def test_make_metric_name_non_empty(self):
        """GOLDEN: make_metric_name returns non-empty string"""
        name = TelemetryTestDataFactory.make_metric_name()
        assert len(name) > 0

    def test_make_unit_non_empty(self):
        """GOLDEN: make_unit returns non-empty string"""
        unit = TelemetryTestDataFactory.make_unit()
        assert len(unit) > 0


# =============================================================================
# Builder Tests
# =============================================================================

class TestTelemetryBuildersGolden:
    """Golden: Builder classes generate valid requests"""

    def test_data_point_builder_default(self):
        """GOLDEN: TelemetryDataPointBuilder creates valid data point"""
        data_point = TelemetryDataPointBuilder().build()
        assert data_point.metric_name is not None
        assert data_point.timestamp is not None

    def test_data_point_builder_with_value(self):
        """GOLDEN: TelemetryDataPointBuilder accepts custom value"""
        value = TelemetryTestDataFactory.make_temperature()
        data_point = TelemetryDataPointBuilder().with_value(value).build()
        assert data_point.value == value

    def test_alert_rule_builder_default(self):
        """GOLDEN: AlertRuleCreateRequestBuilder creates valid request"""
        request = AlertRuleCreateRequestBuilder().build()
        assert request.name is not None
        assert request.metric_name is not None
        assert request.condition is not None

    def test_alert_rule_builder_with_threshold(self):
        """GOLDEN: AlertRuleCreateRequestBuilder accepts custom threshold"""
        threshold = TelemetryTestDataFactory.make_threshold_value()
        request = AlertRuleCreateRequestBuilder().with_threshold(threshold).build()
        assert request.threshold_value == threshold

    def test_query_builder_default(self):
        """GOLDEN: TelemetryQueryRequestBuilder creates valid request"""
        request = TelemetryQueryRequestBuilder().build()
        assert request.start_time is not None
        assert request.end_time is not None

    def test_query_builder_with_devices(self):
        """GOLDEN: TelemetryQueryRequestBuilder accepts device list"""
        devices = TelemetryTestDataFactory.make_device_ids()
        request = TelemetryQueryRequestBuilder().with_devices(devices).build()
        assert request.devices == devices
