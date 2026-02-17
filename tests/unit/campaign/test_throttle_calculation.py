"""
Unit Tests for Throttle/Rate Limit Calculations

Tests rate limiting and throttle calculations per logic_contract.md.
Reference: BR-CAM-006 (Rate Limiting and Throttling)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    ThrottleConfig,
    CampaignTestDataFactory,
)


class ThrottleCalculator:
    """
    Throttle calculation implementation for testing.

    Reference: BR-CAM-006 (Rate Limiting and Throttling)
    - BR-CAM-006.1: Rate limits (10K/min, 100K/hour defaults)
    - BR-CAM-006.2: Organization-level rate limit pooling
    - BR-CAM-006.4: Dynamic throttle reduction on errors
    """

    DEFAULT_RATE_PER_MINUTE = 10000
    DEFAULT_RATE_PER_HOUR = 100000

    @staticmethod
    def get_effective_rate(
        throttle_config: ThrottleConfig = None,
        org_rate_limit: int = None,
        concurrent_campaigns: int = 1,
    ) -> tuple:
        """
        Calculate effective rate limits - BR-CAM-006.1, BR-CAM-006.2

        Args:
            throttle_config: Campaign-specific throttle configuration
            org_rate_limit: Organization-wide rate limit
            concurrent_campaigns: Number of concurrent campaigns sharing rate

        Returns:
            (per_minute, per_hour) tuple of effective rates
        """
        # Start with defaults
        per_minute = ThrottleCalculator.DEFAULT_RATE_PER_MINUTE
        per_hour = ThrottleCalculator.DEFAULT_RATE_PER_HOUR

        # Apply campaign-specific throttle if set
        if throttle_config:
            if throttle_config.per_minute:
                per_minute = min(per_minute, throttle_config.per_minute)
            if throttle_config.per_hour:
                per_hour = min(per_hour, throttle_config.per_hour)

        # Apply organization rate limit - BR-CAM-006.2
        if org_rate_limit:
            per_minute = min(per_minute, org_rate_limit)
            # When org_rate_limit is set, calculate hourly from the effective per_minute
            per_hour = per_minute * 60

        # Split rate among concurrent campaigns - BR-CAM-006.2
        if concurrent_campaigns > 1:
            per_minute = per_minute // concurrent_campaigns
            per_hour = per_hour // concurrent_campaigns

        return per_minute, per_hour

    @staticmethod
    def calculate_dynamic_throttle(
        current_rate: int, error_rate: float, threshold: float = 0.01
    ) -> int:
        """
        Calculate dynamic throttle based on error rate - BR-CAM-006.4

        If bounce/error rate > threshold, reduce rate by 50%
        """
        if error_rate > threshold:
            return current_rate // 2
        return current_rate

    @staticmethod
    def calculate_batch_size(
        total_messages: int, rate_per_minute: int, desired_duration_minutes: int = None
    ) -> int:
        """
        Calculate optimal batch size for message sending

        Args:
            total_messages: Total messages to send
            rate_per_minute: Messages per minute limit
            desired_duration_minutes: Target duration (optional)

        Returns:
            Recommended batch size
        """
        if desired_duration_minutes:
            # Spread messages over desired duration
            batch_size = total_messages // desired_duration_minutes
            return min(batch_size, rate_per_minute)
        else:
            # Use rate limit as batch size
            return min(total_messages, rate_per_minute)

    @staticmethod
    def estimate_completion_time(
        total_messages: int, rate_per_minute: int
    ) -> timedelta:
        """
        Estimate campaign completion time based on rate limits

        Returns:
            Estimated duration as timedelta
        """
        if rate_per_minute <= 0:
            raise ValueError("Rate must be positive")

        minutes_needed = total_messages / rate_per_minute
        return timedelta(minutes=minutes_needed)

    @staticmethod
    def is_within_window(
        current_time: datetime,
        window_start: int,
        window_end: int,
        user_timezone: str = "UTC",
    ) -> bool:
        """
        Check if current time is within send window - BR-CAM-006.1

        Args:
            current_time: Current datetime
            window_start: Start hour (0-23)
            window_end: End hour (0-23)
            user_timezone: User's timezone

        Returns:
            True if within send window
        """
        # For simplicity, assume UTC if timezone conversion needed
        current_hour = current_time.hour

        if window_start < window_end:
            # Normal range (e.g., 8-21)
            return window_start <= current_hour < window_end
        else:
            # Overnight range (e.g., 22-6)
            return current_hour >= window_start or current_hour < window_end

    @staticmethod
    def is_weekend(current_time: datetime) -> bool:
        """Check if current time is weekend"""
        return current_time.weekday() >= 5  # Saturday=5, Sunday=6


# ====================
# Default Rate Tests
# ====================


class TestDefaultRates:
    """Tests for default rate limits - BR-CAM-006.1"""

    def test_default_rate_per_minute(self):
        """Test default rate is 10K/minute"""
        per_minute, _ = ThrottleCalculator.get_effective_rate()
        assert per_minute == 10000

    def test_default_rate_per_hour(self):
        """Test default rate is 100K/hour"""
        _, per_hour = ThrottleCalculator.get_effective_rate()
        assert per_hour == 100000

    def test_no_throttle_config_uses_defaults(self):
        """Test no throttle config uses default rates"""
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(throttle_config=None)
        assert per_minute == ThrottleCalculator.DEFAULT_RATE_PER_MINUTE
        assert per_hour == ThrottleCalculator.DEFAULT_RATE_PER_HOUR


# ====================
# Campaign Throttle Tests
# ====================


class TestCampaignThrottle:
    """Tests for campaign-specific throttle configuration"""

    def test_throttle_config_lower_than_default(self):
        """Test campaign throttle lower than default is used"""
        config = ThrottleConfig(per_minute=5000, per_hour=50000)
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            throttle_config=config
        )
        assert per_minute == 5000
        assert per_hour == 50000

    def test_throttle_config_higher_than_default_capped(self):
        """Test campaign throttle higher than default is capped"""
        config = ThrottleConfig(per_minute=20000, per_hour=200000)
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            throttle_config=config
        )
        # Should be capped at defaults
        assert per_minute == 10000
        assert per_hour == 100000

    def test_throttle_config_partial_only_minute(self):
        """Test throttle config with only per_minute"""
        config = ThrottleConfig(per_minute=3000)
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            throttle_config=config
        )
        assert per_minute == 3000
        assert per_hour == 100000  # Default


# ====================
# Organization Rate Limit Tests
# ====================


class TestOrganizationRateLimit:
    """Tests for organization-level rate limiting - BR-CAM-006.2"""

    def test_org_rate_limit_applied(self):
        """Test organization rate limit is applied"""
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            org_rate_limit=5000
        )
        assert per_minute == 5000
        assert per_hour == 300000  # 5000 * 60

    def test_org_rate_limit_lower_than_campaign(self):
        """Test org limit takes precedence when lower"""
        config = ThrottleConfig(per_minute=8000)
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            throttle_config=config, org_rate_limit=3000
        )
        assert per_minute == 3000  # Org limit is lower

    def test_concurrent_campaigns_share_rate(self):
        """Test rate is split among concurrent campaigns - BR-CAM-006.2"""
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            concurrent_campaigns=4
        )
        assert per_minute == 2500  # 10000 / 4
        assert per_hour == 25000  # 100000 / 4

    def test_concurrent_campaigns_with_org_limit(self):
        """Test concurrent campaigns with org limit"""
        per_minute, per_hour = ThrottleCalculator.get_effective_rate(
            org_rate_limit=8000, concurrent_campaigns=2
        )
        assert per_minute == 4000  # 8000 / 2


# ====================
# Dynamic Throttle Tests
# ====================


class TestDynamicThrottle:
    """Tests for dynamic throttle adjustment - BR-CAM-006.4"""

    def test_no_errors_keeps_rate(self):
        """Test no errors keeps original rate"""
        result = ThrottleCalculator.calculate_dynamic_throttle(
            current_rate=10000, error_rate=0.0
        )
        assert result == 10000

    def test_low_error_rate_keeps_rate(self):
        """Test error rate below threshold keeps rate"""
        result = ThrottleCalculator.calculate_dynamic_throttle(
            current_rate=10000, error_rate=0.005  # 0.5% < 1%
        )
        assert result == 10000

    def test_high_error_rate_reduces_rate(self):
        """Test error rate above threshold reduces rate by 50%"""
        result = ThrottleCalculator.calculate_dynamic_throttle(
            current_rate=10000, error_rate=0.02  # 2% > 1%
        )
        assert result == 5000

    def test_custom_threshold(self):
        """Test custom error threshold"""
        # With 5% threshold, 2% error rate is ok
        result = ThrottleCalculator.calculate_dynamic_throttle(
            current_rate=10000, error_rate=0.02, threshold=0.05
        )
        assert result == 10000

        # But 6% would trigger reduction
        result = ThrottleCalculator.calculate_dynamic_throttle(
            current_rate=10000, error_rate=0.06, threshold=0.05
        )
        assert result == 5000


# ====================
# Batch Size Tests
# ====================


class TestBatchSizeCalculation:
    """Tests for batch size calculation"""

    def test_batch_size_small_audience(self):
        """Test batch size for small audience fits in one batch"""
        batch_size = ThrottleCalculator.calculate_batch_size(
            total_messages=500, rate_per_minute=10000
        )
        assert batch_size == 500  # All messages in one batch

    def test_batch_size_large_audience(self):
        """Test batch size for large audience respects rate limit"""
        batch_size = ThrottleCalculator.calculate_batch_size(
            total_messages=50000, rate_per_minute=10000
        )
        assert batch_size == 10000  # Capped at rate limit

    def test_batch_size_with_duration(self):
        """Test batch size spread over desired duration"""
        batch_size = ThrottleCalculator.calculate_batch_size(
            total_messages=60000, rate_per_minute=10000, desired_duration_minutes=30
        )
        assert batch_size == 2000  # 60000 / 30

    def test_batch_size_duration_exceeds_rate(self):
        """Test batch size capped at rate even with duration"""
        batch_size = ThrottleCalculator.calculate_batch_size(
            total_messages=100000,
            rate_per_minute=5000,
            desired_duration_minutes=5,  # Would need 20000/min
        )
        assert batch_size == 5000  # Capped at rate limit


# ====================
# Completion Time Tests
# ====================


class TestCompletionTimeEstimate:
    """Tests for completion time estimation"""

    def test_small_campaign_completion(self):
        """Test completion time for small campaign"""
        duration = ThrottleCalculator.estimate_completion_time(
            total_messages=5000, rate_per_minute=10000
        )
        assert duration == timedelta(minutes=0.5)

    def test_large_campaign_completion(self):
        """Test completion time for large campaign"""
        duration = ThrottleCalculator.estimate_completion_time(
            total_messages=100000, rate_per_minute=10000
        )
        assert duration == timedelta(minutes=10)

    def test_very_large_campaign_completion(self):
        """Test completion time for very large campaign"""
        duration = ThrottleCalculator.estimate_completion_time(
            total_messages=1000000, rate_per_minute=10000
        )
        assert duration == timedelta(minutes=100)  # 1h 40m

    def test_zero_rate_raises_error(self):
        """Test zero rate raises error"""
        with pytest.raises(ValueError):
            ThrottleCalculator.estimate_completion_time(
                total_messages=1000, rate_per_minute=0
            )


# ====================
# Send Window Tests
# ====================


class TestSendWindow:
    """Tests for send window checking - BR-CAM-006.1"""

    def test_within_normal_window(self):
        """Test time within normal window (8-21)"""
        time = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)  # 2pm
        assert ThrottleCalculator.is_within_window(time, window_start=8, window_end=21)

    def test_outside_normal_window_early(self):
        """Test time outside normal window (too early)"""
        time = datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc)  # 6am
        assert not ThrottleCalculator.is_within_window(time, window_start=8, window_end=21)

    def test_outside_normal_window_late(self):
        """Test time outside normal window (too late)"""
        time = datetime(2026, 1, 15, 22, 0, tzinfo=timezone.utc)  # 10pm
        assert not ThrottleCalculator.is_within_window(time, window_start=8, window_end=21)

    def test_at_window_start(self):
        """Test time exactly at window start"""
        time = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        assert ThrottleCalculator.is_within_window(time, window_start=8, window_end=21)

    def test_at_window_end_boundary(self):
        """Test time exactly at window end (exclusive)"""
        time = datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)
        assert not ThrottleCalculator.is_within_window(time, window_start=8, window_end=21)

    def test_overnight_window(self):
        """Test overnight window (22-6)"""
        # 11pm should be in window
        time_late = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
        assert ThrottleCalculator.is_within_window(
            time_late, window_start=22, window_end=6
        )

        # 3am should be in window
        time_early = datetime(2026, 1, 15, 3, 0, tzinfo=timezone.utc)
        assert ThrottleCalculator.is_within_window(
            time_early, window_start=22, window_end=6
        )

        # 10am should not be in window
        time_mid = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert not ThrottleCalculator.is_within_window(
            time_mid, window_start=22, window_end=6
        )


# ====================
# Weekend Tests
# ====================


class TestWeekendCheck:
    """Tests for weekend checking"""

    def test_monday_is_not_weekend(self):
        """Test Monday is not weekend"""
        monday = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)  # Monday
        assert not ThrottleCalculator.is_weekend(monday)

    def test_friday_is_not_weekend(self):
        """Test Friday is not weekend"""
        friday = datetime(2026, 1, 16, 12, 0, tzinfo=timezone.utc)  # Friday
        assert not ThrottleCalculator.is_weekend(friday)

    def test_saturday_is_weekend(self):
        """Test Saturday is weekend"""
        saturday = datetime(2026, 1, 17, 12, 0, tzinfo=timezone.utc)  # Saturday
        assert ThrottleCalculator.is_weekend(saturday)

    def test_sunday_is_weekend(self):
        """Test Sunday is weekend"""
        sunday = datetime(2026, 1, 18, 12, 0, tzinfo=timezone.utc)  # Sunday
        assert ThrottleCalculator.is_weekend(sunday)


# ====================
# Parametrized Tests
# ====================


class TestThrottleParametrized:
    """Parametrized throttle tests"""

    @pytest.mark.parametrize(
        "per_minute,per_hour,concurrent,expected_minute,expected_hour",
        [
            (None, None, 1, 10000, 100000),  # Defaults
            (5000, None, 1, 5000, 100000),  # Only minute set
            (None, 50000, 1, 10000, 50000),  # Only hour set
            (5000, 50000, 1, 5000, 50000),  # Both set
            (10000, 100000, 2, 5000, 50000),  # Split between 2
            (10000, 100000, 4, 2500, 25000),  # Split between 4
        ],
    )
    def test_effective_rate_calculation(
        self, per_minute, per_hour, concurrent, expected_minute, expected_hour
    ):
        """Test effective rate calculation with various inputs"""
        config = None
        if per_minute or per_hour:
            config = ThrottleConfig(per_minute=per_minute, per_hour=per_hour)

        result_minute, result_hour = ThrottleCalculator.get_effective_rate(
            throttle_config=config, concurrent_campaigns=concurrent
        )

        assert result_minute == expected_minute
        assert result_hour == expected_hour
