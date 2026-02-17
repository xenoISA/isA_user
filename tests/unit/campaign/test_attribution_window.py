"""
Unit Tests for Conversion Attribution Window Logic

Tests attribution window calculations per logic_contract.md.
Reference: BR-CAM-005.3 (Track Conversions)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    AttributionModel,
    CampaignConversion,
    CampaignTestDataFactory,
)


class AttributionCalculator:
    """
    Attribution window and model calculation implementation for testing.

    Reference: BR-CAM-005.3 (Track Conversions)

    Models:
    - FIRST_TOUCH: Credit goes to first message that touched user
    - LAST_TOUCH: Credit goes to most recent message before conversion
    - LINEAR: Credit split equally among all touches
    """

    DEFAULT_WINDOW_DAYS = 7

    @staticmethod
    def is_within_attribution_window(
        message_delivered_at: datetime,
        conversion_at: datetime,
        window_days: int = None,
    ) -> bool:
        """
        Check if conversion is within attribution window - BR-CAM-005.3

        Args:
            message_delivered_at: When message was delivered
            conversion_at: When conversion occurred
            window_days: Attribution window in days (default 7, max 30)

        Returns:
            True if conversion is within attribution window
        """
        if window_days is None:
            window_days = AttributionCalculator.DEFAULT_WINDOW_DAYS

        # Validate window (max 30 days per logic_contract)
        window_days = min(window_days, 30)

        if conversion_at < message_delivered_at:
            return False  # Conversion before message - not attributable

        time_diff = conversion_at - message_delivered_at
        return time_diff <= timedelta(days=window_days)

    @staticmethod
    def find_attributable_messages(
        messages: list,  # List of (message_id, delivered_at)
        conversion_at: datetime,
        window_days: int = None,
    ) -> list:
        """
        Find all messages within attribution window for a conversion.

        Returns list of message_ids that are attributable.
        """
        attributable = []
        for message_id, delivered_at in messages:
            if AttributionCalculator.is_within_attribution_window(
                delivered_at, conversion_at, window_days
            ):
                attributable.append((message_id, delivered_at))
        return attributable

    @staticmethod
    def calculate_attribution_first_touch(
        attributable_messages: list,  # List of (message_id, delivered_at)
        conversion_value: Decimal,
    ) -> dict:
        """
        Calculate attribution using first touch model - BR-CAM-005.3

        Returns: {message_id: attributed_value}
        """
        if not attributable_messages:
            return {}

        # Sort by delivered_at and take first
        sorted_messages = sorted(attributable_messages, key=lambda x: x[1])
        first_message = sorted_messages[0]

        return {first_message[0]: conversion_value}

    @staticmethod
    def calculate_attribution_last_touch(
        attributable_messages: list,  # List of (message_id, delivered_at)
        conversion_value: Decimal,
    ) -> dict:
        """
        Calculate attribution using last touch model - BR-CAM-005.3

        Returns: {message_id: attributed_value}
        """
        if not attributable_messages:
            return {}

        # Sort by delivered_at and take last
        sorted_messages = sorted(attributable_messages, key=lambda x: x[1])
        last_message = sorted_messages[-1]

        return {last_message[0]: conversion_value}

    @staticmethod
    def calculate_attribution_linear(
        attributable_messages: list,  # List of (message_id, delivered_at)
        conversion_value: Decimal,
    ) -> dict:
        """
        Calculate attribution using linear model - BR-CAM-005.3

        Returns: {message_id: attributed_value}
        """
        if not attributable_messages:
            return {}

        num_messages = len(attributable_messages)
        value_per_message = conversion_value / Decimal(str(num_messages))

        return {msg[0]: value_per_message for msg in attributable_messages}

    @staticmethod
    def calculate_attribution(
        attributable_messages: list,
        conversion_value: Decimal,
        model: AttributionModel,
    ) -> dict:
        """
        Calculate attribution based on model - BR-CAM-005.3

        Returns: {message_id: attributed_value}
        """
        if model == AttributionModel.FIRST_TOUCH:
            return AttributionCalculator.calculate_attribution_first_touch(
                attributable_messages, conversion_value
            )
        elif model == AttributionModel.LAST_TOUCH:
            return AttributionCalculator.calculate_attribution_last_touch(
                attributable_messages, conversion_value
            )
        elif model == AttributionModel.LINEAR:
            return AttributionCalculator.calculate_attribution_linear(
                attributable_messages, conversion_value
            )
        else:
            # Default to last touch
            return AttributionCalculator.calculate_attribution_last_touch(
                attributable_messages, conversion_value
            )


# ====================
# Attribution Window Tests
# ====================


class TestAttributionWindow:
    """Tests for attribution window calculation - BR-CAM-005.3"""

    def test_within_default_7_day_window(self):
        """Test conversion within default 7-day window"""
        delivered = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc)

        assert AttributionCalculator.is_within_attribution_window(delivered, converted)

    def test_outside_default_7_day_window(self):
        """Test conversion outside default 7-day window"""
        delivered = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 20, 18, 0, tzinfo=timezone.utc)  # 10 days later

        assert not AttributionCalculator.is_within_attribution_window(
            delivered, converted
        )

    def test_exactly_at_window_boundary(self):
        """Test conversion exactly at 7-day boundary"""
        delivered = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 17, 12, 0, tzinfo=timezone.utc)  # Exactly 7 days

        assert AttributionCalculator.is_within_attribution_window(delivered, converted)

    def test_just_past_window_boundary(self):
        """Test conversion just past 7-day boundary"""
        delivered = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        converted = datetime(
            2026, 1, 17, 12, 1, tzinfo=timezone.utc
        )  # 7 days + 1 minute

        assert not AttributionCalculator.is_within_attribution_window(
            delivered, converted
        )

    def test_custom_30_day_window(self):
        """Test conversion within custom 30-day window"""
        delivered = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 25, 18, 0, tzinfo=timezone.utc)  # 24 days later

        assert AttributionCalculator.is_within_attribution_window(
            delivered, converted, window_days=30
        )

    def test_custom_1_day_window(self):
        """Test conversion within custom 1-day window"""
        delivered = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 10, 18, 0, tzinfo=timezone.utc)  # Same day

        assert AttributionCalculator.is_within_attribution_window(
            delivered, converted, window_days=1
        )

    def test_conversion_before_message_not_attributable(self):
        """Test conversion before message delivery is not attributable"""
        delivered = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 1, 10, 18, 0, tzinfo=timezone.utc)  # Before message

        assert not AttributionCalculator.is_within_attribution_window(
            delivered, converted
        )

    def test_window_capped_at_30_days(self):
        """Test window is capped at 30 days max - BR-CAM-005.3"""
        delivered = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        converted = datetime(2026, 2, 5, 18, 0, tzinfo=timezone.utc)  # 35 days later

        # Even with 60 day window, should be capped at 30
        assert not AttributionCalculator.is_within_attribution_window(
            delivered, converted, window_days=60
        )


# ====================
# Find Attributable Messages Tests
# ====================


class TestFindAttributableMessages:
    """Tests for finding attributable messages"""

    def test_all_messages_attributable(self):
        """Test all messages within window are found"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=2)),
            ("msg_2", base_time - timedelta(days=4)),
            ("msg_3", base_time - timedelta(days=6)),
        ]
        conversion_at = base_time

        result = AttributionCalculator.find_attributable_messages(
            messages, conversion_at, window_days=7
        )

        assert len(result) == 3
        assert "msg_1" in [r[0] for r in result]
        assert "msg_2" in [r[0] for r in result]
        assert "msg_3" in [r[0] for r in result]

    def test_some_messages_outside_window(self):
        """Test only messages within window are found"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=2)),  # In window
            ("msg_2", base_time - timedelta(days=10)),  # Outside window
            ("msg_3", base_time - timedelta(days=5)),  # In window
        ]
        conversion_at = base_time

        result = AttributionCalculator.find_attributable_messages(
            messages, conversion_at, window_days=7
        )

        assert len(result) == 2
        assert "msg_1" in [r[0] for r in result]
        assert "msg_3" in [r[0] for r in result]
        assert "msg_2" not in [r[0] for r in result]

    def test_no_messages_attributable(self):
        """Test no messages found when all outside window"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=10)),
            ("msg_2", base_time - timedelta(days=15)),
        ]
        conversion_at = base_time

        result = AttributionCalculator.find_attributable_messages(
            messages, conversion_at, window_days=7
        )

        assert len(result) == 0


# ====================
# First Touch Attribution Tests
# ====================


class TestFirstTouchAttribution:
    """Tests for first touch attribution model - BR-CAM-005.3"""

    def test_first_touch_single_message(self):
        """Test first touch with single message"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [("msg_1", base_time - timedelta(days=2))]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_first_touch(
            messages, conversion_value
        )

        assert result == {"msg_1": Decimal("100.00")}

    def test_first_touch_multiple_messages(self):
        """Test first touch with multiple messages (earliest gets credit)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_recent", base_time - timedelta(days=1)),  # Most recent
            ("msg_old", base_time - timedelta(days=5)),  # Oldest
            ("msg_middle", base_time - timedelta(days=3)),  # Middle
        ]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_first_touch(
            messages, conversion_value
        )

        # Only oldest message gets credit
        assert result == {"msg_old": Decimal("100.00")}
        assert "msg_recent" not in result
        assert "msg_middle" not in result

    def test_first_touch_no_messages(self):
        """Test first touch with no messages returns empty"""
        result = AttributionCalculator.calculate_attribution_first_touch(
            [], Decimal("100.00")
        )
        assert result == {}


# ====================
# Last Touch Attribution Tests
# ====================


class TestLastTouchAttribution:
    """Tests for last touch attribution model - BR-CAM-005.3"""

    def test_last_touch_single_message(self):
        """Test last touch with single message"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [("msg_1", base_time - timedelta(days=2))]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_last_touch(
            messages, conversion_value
        )

        assert result == {"msg_1": Decimal("100.00")}

    def test_last_touch_multiple_messages(self):
        """Test last touch with multiple messages (most recent gets credit)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_recent", base_time - timedelta(days=1)),  # Most recent
            ("msg_old", base_time - timedelta(days=5)),  # Oldest
            ("msg_middle", base_time - timedelta(days=3)),  # Middle
        ]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_last_touch(
            messages, conversion_value
        )

        # Only most recent message gets credit
        assert result == {"msg_recent": Decimal("100.00")}
        assert "msg_old" not in result
        assert "msg_middle" not in result

    def test_last_touch_no_messages(self):
        """Test last touch with no messages returns empty"""
        result = AttributionCalculator.calculate_attribution_last_touch(
            [], Decimal("100.00")
        )
        assert result == {}


# ====================
# Linear Attribution Tests
# ====================


class TestLinearAttribution:
    """Tests for linear attribution model - BR-CAM-005.3"""

    def test_linear_single_message(self):
        """Test linear with single message (gets 100%)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [("msg_1", base_time - timedelta(days=2))]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_linear(
            messages, conversion_value
        )

        assert result == {"msg_1": Decimal("100.00")}

    def test_linear_two_messages(self):
        """Test linear with two messages (50% each)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=2)),
            ("msg_2", base_time - timedelta(days=4)),
        ]
        conversion_value = Decimal("100.00")

        result = AttributionCalculator.calculate_attribution_linear(
            messages, conversion_value
        )

        assert result["msg_1"] == Decimal("50.00")
        assert result["msg_2"] == Decimal("50.00")

    def test_linear_three_messages(self):
        """Test linear with three messages (33.33% each)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=1)),
            ("msg_2", base_time - timedelta(days=3)),
            ("msg_3", base_time - timedelta(days=5)),
        ]
        conversion_value = Decimal("99.00")  # Divides evenly by 3

        result = AttributionCalculator.calculate_attribution_linear(
            messages, conversion_value
        )

        assert result["msg_1"] == Decimal("33.00")
        assert result["msg_2"] == Decimal("33.00")
        assert result["msg_3"] == Decimal("33.00")

    def test_linear_no_messages(self):
        """Test linear with no messages returns empty"""
        result = AttributionCalculator.calculate_attribution_linear([], Decimal("100.00"))
        assert result == {}


# ====================
# Model Selection Tests
# ====================


class TestAttributionModelSelection:
    """Tests for attribution model selection"""

    def test_calculate_with_first_touch_model(self):
        """Test calculate_attribution with FIRST_TOUCH model"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_recent", base_time - timedelta(days=1)),
            ("msg_old", base_time - timedelta(days=5)),
        ]

        result = AttributionCalculator.calculate_attribution(
            messages, Decimal("100.00"), AttributionModel.FIRST_TOUCH
        )

        assert "msg_old" in result
        assert "msg_recent" not in result

    def test_calculate_with_last_touch_model(self):
        """Test calculate_attribution with LAST_TOUCH model"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_recent", base_time - timedelta(days=1)),
            ("msg_old", base_time - timedelta(days=5)),
        ]

        result = AttributionCalculator.calculate_attribution(
            messages, Decimal("100.00"), AttributionModel.LAST_TOUCH
        )

        assert "msg_recent" in result
        assert "msg_old" not in result

    def test_calculate_with_linear_model(self):
        """Test calculate_attribution with LINEAR model"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=1)),
            ("msg_2", base_time - timedelta(days=3)),
        ]

        result = AttributionCalculator.calculate_attribution(
            messages, Decimal("100.00"), AttributionModel.LINEAR
        )

        assert len(result) == 2
        assert result["msg_1"] == Decimal("50.00")
        assert result["msg_2"] == Decimal("50.00")


# ====================
# Edge Cases
# ====================


class TestAttributionEdgeCases:
    """Tests for attribution edge cases"""

    def test_same_timestamp_messages(self):
        """Test messages with same timestamp"""
        same_time = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", same_time),
            ("msg_2", same_time),
        ]
        conversion_value = Decimal("100.00")

        # With same timestamp, behavior depends on list order (stable sort)
        result_first = AttributionCalculator.calculate_attribution_first_touch(
            messages, conversion_value
        )
        result_last = AttributionCalculator.calculate_attribution_last_touch(
            messages, conversion_value
        )

        # Both should attribute to one message
        assert len(result_first) == 1
        assert len(result_last) == 1

    def test_zero_conversion_value(self):
        """Test attribution with zero conversion value"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=2)),
            ("msg_2", base_time - timedelta(days=4)),
        ]

        result = AttributionCalculator.calculate_attribution_linear(
            messages, Decimal("0.00")
        )

        assert result["msg_1"] == Decimal("0.00")
        assert result["msg_2"] == Decimal("0.00")

    def test_very_small_conversion_value(self):
        """Test attribution with very small value (precision)"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_1", base_time - timedelta(days=1)),
            ("msg_2", base_time - timedelta(days=2)),
            ("msg_3", base_time - timedelta(days=3)),
        ]

        result = AttributionCalculator.calculate_attribution_linear(
            messages, Decimal("0.01")  # 1 cent split 3 ways
        )

        # Verify total is preserved (may have rounding)
        total = sum(result.values())
        # Due to division, might be 0.0033... each
        assert total <= Decimal("0.01")


# ====================
# Parametrized Tests
# ====================


class TestAttributionParametrized:
    """Parametrized attribution tests"""

    @pytest.mark.parametrize(
        "window_days,days_diff,expected",
        [
            (7, 0, True),  # Same day
            (7, 6, True),  # Within window
            (7, 7, True),  # At boundary
            (7, 8, False),  # Past window
            (30, 25, True),  # Long window
            (30, 31, False),  # Past long window
            (1, 1, True),  # Short window at boundary
            (1, 2, False),  # Past short window
        ],
    )
    def test_window_boundary_scenarios(self, window_days, days_diff, expected):
        """Test various window boundary scenarios"""
        delivered = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        converted = delivered + timedelta(days=days_diff)

        result = AttributionCalculator.is_within_attribution_window(
            delivered, converted, window_days=window_days
        )
        assert result == expected

    @pytest.mark.parametrize(
        "model,expected_key",
        [
            (AttributionModel.FIRST_TOUCH, "msg_old"),
            (AttributionModel.LAST_TOUCH, "msg_recent"),
        ],
    )
    def test_attribution_model_selection(self, model, expected_key):
        """Test correct message selected by model"""
        base_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        messages = [
            ("msg_recent", base_time - timedelta(days=1)),
            ("msg_old", base_time - timedelta(days=5)),
        ]

        result = AttributionCalculator.calculate_attribution(
            messages, Decimal("100.00"), model
        )

        assert expected_key in result
        assert result[expected_key] == Decimal("100.00")
