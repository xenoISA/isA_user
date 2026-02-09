"""
Unit Tests for Quiet Hours Enforcement Logic

Tests quiet hours enforcement per logic_contract.md.
Reference: BR-CAM-006.3 (Quiet Hours Enforcement)
"""

import pytest
from datetime import datetime, timezone, timedelta

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import CampaignTestDataFactory


class QuietHoursEnforcer:
    """
    Quiet hours enforcement implementation for testing.

    Reference: BR-CAM-006.3 (Quiet Hours Enforcement)
    Default quiet hours: 21:00-08:00 in user's timezone
    """

    DEFAULT_QUIET_START = 21  # 9 PM
    DEFAULT_QUIET_END = 8  # 8 AM

    @staticmethod
    def is_quiet_hours(
        current_time: datetime,
        quiet_start: int = None,
        quiet_end: int = None,
    ) -> bool:
        """
        Check if current time is within quiet hours - BR-CAM-006.3

        Args:
            current_time: Current datetime (in user's timezone)
            quiet_start: Start of quiet hours (0-23), default 21
            quiet_end: End of quiet hours (0-23), default 8

        Returns:
            True if within quiet hours
        """
        quiet_start = (
            quiet_start if quiet_start is not None else QuietHoursEnforcer.DEFAULT_QUIET_START
        )
        quiet_end = quiet_end if quiet_end is not None else QuietHoursEnforcer.DEFAULT_QUIET_END

        current_hour = current_time.hour

        if quiet_start > quiet_end:
            # Overnight quiet hours (e.g., 21:00 - 08:00)
            return current_hour >= quiet_start or current_hour < quiet_end
        else:
            # Same-day quiet hours (e.g., 14:00 - 18:00, unusual but supported)
            return quiet_start <= current_hour < quiet_end

    @staticmethod
    def get_next_send_time(
        current_time: datetime,
        quiet_start: int = None,
        quiet_end: int = None,
    ) -> datetime:
        """
        Calculate next available send time after quiet hours - BR-CAM-006.3

        Returns:
            Next datetime when messages can be sent
        """
        quiet_start = (
            quiet_start if quiet_start is not None else QuietHoursEnforcer.DEFAULT_QUIET_START
        )
        quiet_end = quiet_end if quiet_end is not None else QuietHoursEnforcer.DEFAULT_QUIET_END

        if not QuietHoursEnforcer.is_quiet_hours(current_time, quiet_start, quiet_end):
            return current_time  # Already outside quiet hours

        # Calculate next quiet_end time
        next_send = current_time.replace(hour=quiet_end, minute=0, second=0, microsecond=0)

        # If quiet_end is already passed today (overnight case), add a day
        if next_send <= current_time:
            next_send += timedelta(days=1)

        return next_send

    @staticmethod
    def should_delay_message(
        send_time: datetime,
        quiet_start: int = None,
        quiet_end: int = None,
    ) -> tuple:
        """
        Determine if message should be delayed due to quiet hours

        Returns:
            (should_delay: bool, delay_until: datetime or None)
        """
        if QuietHoursEnforcer.is_quiet_hours(send_time, quiet_start, quiet_end):
            delay_until = QuietHoursEnforcer.get_next_send_time(
                send_time, quiet_start, quiet_end
            )
            return True, delay_until
        return False, None

    @staticmethod
    def calculate_delay_duration(current_time: datetime, delay_until: datetime) -> timedelta:
        """Calculate duration of delay"""
        if delay_until <= current_time:
            return timedelta(0)
        return delay_until - current_time


# ====================
# Quiet Hours Detection Tests
# ====================


class TestQuietHoursDetection:
    """Tests for quiet hours detection - BR-CAM-006.3"""

    def test_default_quiet_hours_at_10pm(self):
        """Test 10pm is within default quiet hours (21:00-08:00)"""
        time = datetime(2026, 1, 15, 22, 0, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)

    def test_default_quiet_hours_at_midnight(self):
        """Test midnight is within default quiet hours"""
        time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)

    def test_default_quiet_hours_at_5am(self):
        """Test 5am is within default quiet hours"""
        time = datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)

    def test_default_quiet_hours_at_7am(self):
        """Test 7am is within default quiet hours (before 8am)"""
        time = datetime(2026, 1, 15, 7, 30, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)

    def test_not_quiet_hours_at_8am(self):
        """Test 8am is outside default quiet hours"""
        time = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        assert not QuietHoursEnforcer.is_quiet_hours(time)

    def test_not_quiet_hours_at_noon(self):
        """Test noon is outside default quiet hours"""
        time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        assert not QuietHoursEnforcer.is_quiet_hours(time)

    def test_not_quiet_hours_at_8pm(self):
        """Test 8pm (20:00) is outside default quiet hours"""
        time = datetime(2026, 1, 15, 20, 0, tzinfo=timezone.utc)
        assert not QuietHoursEnforcer.is_quiet_hours(time)

    def test_quiet_hours_boundary_at_9pm(self):
        """Test 9pm (21:00) is start of quiet hours"""
        time = datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)

    def test_quiet_hours_boundary_before_9pm(self):
        """Test 8:59pm is not quiet hours"""
        time = datetime(2026, 1, 15, 20, 59, tzinfo=timezone.utc)
        assert not QuietHoursEnforcer.is_quiet_hours(time)


# ====================
# Custom Quiet Hours Tests
# ====================


class TestCustomQuietHours:
    """Tests for custom quiet hours configuration"""

    def test_custom_quiet_hours_later_start(self):
        """Test custom quiet hours starting at 10pm"""
        time_in = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
        time_out = datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)

        assert QuietHoursEnforcer.is_quiet_hours(time_in, quiet_start=22, quiet_end=8)
        assert not QuietHoursEnforcer.is_quiet_hours(time_out, quiet_start=22, quiet_end=8)

    def test_custom_quiet_hours_earlier_end(self):
        """Test custom quiet hours ending at 6am"""
        time_in = datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)
        time_out = datetime(2026, 1, 15, 7, 0, tzinfo=timezone.utc)

        assert QuietHoursEnforcer.is_quiet_hours(time_in, quiet_start=21, quiet_end=6)
        assert not QuietHoursEnforcer.is_quiet_hours(time_out, quiet_start=21, quiet_end=6)

    def test_same_day_quiet_hours(self):
        """Test quiet hours that don't span midnight (unusual but supported)"""
        # Quiet from 14:00 to 18:00 (e.g., siesta)
        time_in = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)
        time_out = datetime(2026, 1, 15, 19, 0, tzinfo=timezone.utc)

        assert QuietHoursEnforcer.is_quiet_hours(time_in, quiet_start=14, quiet_end=18)
        assert not QuietHoursEnforcer.is_quiet_hours(time_out, quiet_start=14, quiet_end=18)

    def test_no_quiet_hours_same_values(self):
        """Test no quiet hours when start == end"""
        time = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)
        # When start == end, no time is considered quiet
        assert not QuietHoursEnforcer.is_quiet_hours(time, quiet_start=8, quiet_end=8)


# ====================
# Next Send Time Tests
# ====================


class TestNextSendTime:
    """Tests for calculating next send time - BR-CAM-006.3"""

    def test_outside_quiet_hours_returns_current(self):
        """Test time outside quiet hours returns current time"""
        time = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.get_next_send_time(time)
        assert result == time

    def test_during_quiet_hours_returns_next_morning(self):
        """Test time during quiet hours returns 8am next day"""
        time = datetime(2026, 1, 15, 22, 0, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.get_next_send_time(time)
        expected = datetime(2026, 1, 16, 8, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_during_early_morning_quiet_hours(self):
        """Test early morning during quiet hours returns 8am same day"""
        time = datetime(2026, 1, 15, 3, 0, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.get_next_send_time(time)
        expected = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_at_quiet_hours_start(self):
        """Test exactly at quiet hours start"""
        time = datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.get_next_send_time(time)
        expected = datetime(2026, 1, 16, 8, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_just_before_quiet_hours_end(self):
        """Test just before quiet hours end"""
        time = datetime(2026, 1, 15, 7, 59, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.get_next_send_time(time)
        expected = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
        assert result == expected


# ====================
# Message Delay Tests
# ====================


class TestMessageDelay:
    """Tests for message delay decisions"""

    def test_should_not_delay_during_day(self):
        """Test messages not delayed during day"""
        time = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        should_delay, delay_until = QuietHoursEnforcer.should_delay_message(time)
        assert not should_delay
        assert delay_until is None

    def test_should_delay_during_quiet_hours(self):
        """Test messages delayed during quiet hours"""
        time = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
        should_delay, delay_until = QuietHoursEnforcer.should_delay_message(time)
        assert should_delay
        assert delay_until == datetime(2026, 1, 16, 8, 0, tzinfo=timezone.utc)

    def test_delay_duration_overnight(self):
        """Test delay duration calculation for overnight delay"""
        current = datetime(2026, 1, 15, 22, 0, tzinfo=timezone.utc)  # 10pm
        delay_until = datetime(2026, 1, 16, 8, 0, tzinfo=timezone.utc)  # 8am next day

        duration = QuietHoursEnforcer.calculate_delay_duration(current, delay_until)
        assert duration == timedelta(hours=10)

    def test_delay_duration_early_morning(self):
        """Test delay duration calculation for early morning"""
        current = datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)  # 5am
        delay_until = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)  # 8am same day

        duration = QuietHoursEnforcer.calculate_delay_duration(current, delay_until)
        assert duration == timedelta(hours=3)


# ====================
# Edge Cases
# ====================


class TestQuietHoursEdgeCases:
    """Tests for edge cases in quiet hours"""

    def test_midnight_boundary(self):
        """Test midnight boundary handling"""
        just_before_midnight = datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc)
        midnight = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)
        just_after_midnight = datetime(2026, 1, 16, 0, 1, tzinfo=timezone.utc)

        assert QuietHoursEnforcer.is_quiet_hours(just_before_midnight)
        assert QuietHoursEnforcer.is_quiet_hours(midnight)
        assert QuietHoursEnforcer.is_quiet_hours(just_after_midnight)

    def test_year_boundary(self):
        """Test quiet hours across year boundary"""
        new_years_eve_late = datetime(2025, 12, 31, 23, 0, tzinfo=timezone.utc)
        new_years_early = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        assert QuietHoursEnforcer.is_quiet_hours(new_years_eve_late)
        assert QuietHoursEnforcer.is_quiet_hours(new_years_early)

    def test_dst_transition_awareness(self):
        """Test quiet hours should be in user's local time"""
        # This is a simplification - real implementation would handle TZ
        # Here we just verify the hour-based logic works
        time = datetime(2026, 3, 8, 22, 0, tzinfo=timezone.utc)
        assert QuietHoursEnforcer.is_quiet_hours(time)


# ====================
# Parametrized Tests
# ====================


class TestQuietHoursParametrized:
    """Parametrized quiet hours tests"""

    @pytest.mark.parametrize(
        "hour,expected_quiet",
        [
            (0, True),  # Midnight
            (1, True),
            (2, True),
            (3, True),
            (4, True),
            (5, True),
            (6, True),
            (7, True),
            (8, False),  # Start of day
            (9, False),
            (10, False),
            (11, False),
            (12, False),  # Noon
            (13, False),
            (14, False),
            (15, False),
            (16, False),
            (17, False),
            (18, False),
            (19, False),
            (20, False),
            (21, True),  # Start of quiet hours
            (22, True),
            (23, True),
        ],
    )
    def test_default_quiet_hours_by_hour(self, hour, expected_quiet):
        """Test default quiet hours for each hour of day"""
        time = datetime(2026, 1, 15, hour, 0, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.is_quiet_hours(time)
        assert result == expected_quiet, f"Hour {hour} quiet={result}, expected={expected_quiet}"

    @pytest.mark.parametrize(
        "quiet_start,quiet_end,test_hour,expected",
        [
            (21, 8, 22, True),  # Default overnight
            (21, 8, 10, False),
            (22, 6, 23, True),  # Later start, earlier end
            (22, 6, 7, False),
            (0, 6, 3, True),  # Midnight to 6am
            (0, 6, 7, False),
            (14, 18, 15, True),  # Afternoon quiet
            (14, 18, 19, False),
        ],
    )
    def test_custom_quiet_hours_scenarios(
        self, quiet_start, quiet_end, test_hour, expected
    ):
        """Test various custom quiet hours configurations"""
        time = datetime(2026, 1, 15, test_hour, 0, tzinfo=timezone.utc)
        result = QuietHoursEnforcer.is_quiet_hours(
            time, quiet_start=quiet_start, quiet_end=quiet_end
        )
        assert result == expected
