"""
Unit Tests for Message Status State Machine

Tests all valid and invalid message status transitions per logic_contract.md.
Reference: Message Status State Machine (BR-CAM-005.1)
"""

import pytest
from datetime import datetime, timezone

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    MessageStatus,
    BounceType,
    CampaignTestDataFactory,
)


class MessageStatusMachine:
    """
    Message Status State Machine implementation for testing.

    Valid Transitions:
    - QUEUED -> SENT (sent to provider)
    - SENT -> DELIVERED (provider confirms)
    - SENT -> BOUNCED (delivery failed)
    - SENT -> FAILED (provider error)
    - DELIVERED -> OPENED (email opened)
    - DELIVERED -> CLICKED (link clicked)
    - DELIVERED -> UNSUBSCRIBED (user unsubscribed)
    - OPENED -> CLICKED (user clicked after opening)
    """

    VALID_TRANSITIONS = {
        MessageStatus.QUEUED: {MessageStatus.SENT},
        MessageStatus.SENT: {
            MessageStatus.DELIVERED,
            MessageStatus.BOUNCED,
            MessageStatus.FAILED,
        },
        MessageStatus.DELIVERED: {
            MessageStatus.OPENED,
            MessageStatus.CLICKED,
            MessageStatus.UNSUBSCRIBED,
        },
        MessageStatus.OPENED: {MessageStatus.CLICKED},
        # Terminal states
        MessageStatus.CLICKED: set(),
        MessageStatus.BOUNCED: set(),
        MessageStatus.FAILED: set(),
        MessageStatus.UNSUBSCRIBED: set(),
    }

    # For tracking purposes, these statuses indicate engagement
    ENGAGEMENT_STATUSES = {
        MessageStatus.OPENED,
        MessageStatus.CLICKED,
    }

    # Terminal failure states
    FAILURE_STATUSES = {
        MessageStatus.BOUNCED,
        MessageStatus.FAILED,
    }

    @classmethod
    def can_transition(cls, from_status: MessageStatus, to_status: MessageStatus) -> bool:
        """Check if transition is valid"""
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, set())
        return to_status in valid_targets

    @classmethod
    def is_terminal(cls, status: MessageStatus) -> bool:
        """Check if status is terminal (no further transitions except engagement tracking)"""
        return status in {
            MessageStatus.CLICKED,
            MessageStatus.BOUNCED,
            MessageStatus.FAILED,
            MessageStatus.UNSUBSCRIBED,
        }

    @classmethod
    def is_delivered(cls, status: MessageStatus) -> bool:
        """Check if message was successfully delivered"""
        return status in {
            MessageStatus.DELIVERED,
            MessageStatus.OPENED,
            MessageStatus.CLICKED,
        }

    @classmethod
    def is_engagement(cls, status: MessageStatus) -> bool:
        """Check if status indicates user engagement"""
        return status in cls.ENGAGEMENT_STATUSES

    @classmethod
    def is_failure(cls, status: MessageStatus) -> bool:
        """Check if status indicates delivery failure"""
        return status in cls.FAILURE_STATUSES

    @classmethod
    def get_timestamp_field(cls, status: MessageStatus) -> str:
        """Get the timestamp field name for a status - BR-CAM-005.1"""
        field_mapping = {
            MessageStatus.QUEUED: "queued_at",
            MessageStatus.SENT: "sent_at",
            MessageStatus.DELIVERED: "delivered_at",
            MessageStatus.OPENED: "opened_at",
            MessageStatus.CLICKED: "clicked_at",
            MessageStatus.BOUNCED: "bounced_at",
            MessageStatus.FAILED: "failed_at",
            MessageStatus.UNSUBSCRIBED: "unsubscribed_at",
        }
        return field_mapping.get(status, "updated_at")


# ====================
# Valid Transition Tests
# ====================


class TestValidMessageStatusTransitions:
    """Tests for valid message status transitions - BR-CAM-005.1"""

    def test_queued_to_sent_valid(self):
        """Test QUEUED -> SENT is valid"""
        assert MessageStatusMachine.can_transition(MessageStatus.QUEUED, MessageStatus.SENT)

    def test_sent_to_delivered_valid(self):
        """Test SENT -> DELIVERED is valid"""
        assert MessageStatusMachine.can_transition(MessageStatus.SENT, MessageStatus.DELIVERED)

    def test_sent_to_bounced_valid(self):
        """Test SENT -> BOUNCED is valid"""
        assert MessageStatusMachine.can_transition(MessageStatus.SENT, MessageStatus.BOUNCED)

    def test_sent_to_failed_valid(self):
        """Test SENT -> FAILED is valid"""
        assert MessageStatusMachine.can_transition(MessageStatus.SENT, MessageStatus.FAILED)

    def test_delivered_to_opened_valid(self):
        """Test DELIVERED -> OPENED is valid"""
        assert MessageStatusMachine.can_transition(
            MessageStatus.DELIVERED, MessageStatus.OPENED
        )

    def test_delivered_to_clicked_valid(self):
        """Test DELIVERED -> CLICKED is valid (direct click without open tracking)"""
        assert MessageStatusMachine.can_transition(
            MessageStatus.DELIVERED, MessageStatus.CLICKED
        )

    def test_delivered_to_unsubscribed_valid(self):
        """Test DELIVERED -> UNSUBSCRIBED is valid"""
        assert MessageStatusMachine.can_transition(
            MessageStatus.DELIVERED, MessageStatus.UNSUBSCRIBED
        )

    def test_opened_to_clicked_valid(self):
        """Test OPENED -> CLICKED is valid"""
        assert MessageStatusMachine.can_transition(MessageStatus.OPENED, MessageStatus.CLICKED)


# ====================
# Invalid Transition Tests
# ====================


class TestInvalidMessageStatusTransitions:
    """Tests for invalid message status transitions"""

    def test_queued_to_delivered_invalid(self):
        """Test QUEUED -> DELIVERED is invalid (must go through SENT)"""
        assert not MessageStatusMachine.can_transition(
            MessageStatus.QUEUED, MessageStatus.DELIVERED
        )

    def test_queued_to_opened_invalid(self):
        """Test QUEUED -> OPENED is invalid"""
        assert not MessageStatusMachine.can_transition(
            MessageStatus.QUEUED, MessageStatus.OPENED
        )

    def test_sent_to_opened_invalid(self):
        """Test SENT -> OPENED is invalid (must go through DELIVERED)"""
        assert not MessageStatusMachine.can_transition(
            MessageStatus.SENT, MessageStatus.OPENED
        )

    def test_sent_to_clicked_invalid(self):
        """Test SENT -> CLICKED is invalid (must go through DELIVERED)"""
        assert not MessageStatusMachine.can_transition(
            MessageStatus.SENT, MessageStatus.CLICKED
        )

    def test_bounced_to_any_invalid(self):
        """Test BOUNCED -> any is invalid (terminal state)"""
        for status in MessageStatus:
            if status != MessageStatus.BOUNCED:
                assert not MessageStatusMachine.can_transition(
                    MessageStatus.BOUNCED, status
                ), f"BOUNCED -> {status} should be invalid"

    def test_failed_to_any_invalid(self):
        """Test FAILED -> any is invalid (terminal state)"""
        for status in MessageStatus:
            if status != MessageStatus.FAILED:
                assert not MessageStatusMachine.can_transition(
                    MessageStatus.FAILED, status
                ), f"FAILED -> {status} should be invalid"

    def test_clicked_to_any_invalid(self):
        """Test CLICKED -> any is invalid (terminal engagement state)"""
        for status in MessageStatus:
            if status != MessageStatus.CLICKED:
                assert not MessageStatusMachine.can_transition(
                    MessageStatus.CLICKED, status
                ), f"CLICKED -> {status} should be invalid"

    def test_unsubscribed_to_any_invalid(self):
        """Test UNSUBSCRIBED -> any is invalid (terminal state)"""
        for status in MessageStatus:
            if status != MessageStatus.UNSUBSCRIBED:
                assert not MessageStatusMachine.can_transition(
                    MessageStatus.UNSUBSCRIBED, status
                ), f"UNSUBSCRIBED -> {status} should be invalid"

    def test_reverse_transitions_invalid(self):
        """Test reverse transitions are invalid"""
        # Can't go backwards
        assert not MessageStatusMachine.can_transition(
            MessageStatus.SENT, MessageStatus.QUEUED
        )
        assert not MessageStatusMachine.can_transition(
            MessageStatus.DELIVERED, MessageStatus.SENT
        )
        assert not MessageStatusMachine.can_transition(
            MessageStatus.OPENED, MessageStatus.DELIVERED
        )


# ====================
# Terminal State Tests
# ====================


class TestTerminalMessageStates:
    """Tests for terminal message state identification"""

    def test_clicked_is_terminal(self):
        """Test CLICKED is terminal"""
        assert MessageStatusMachine.is_terminal(MessageStatus.CLICKED)

    def test_bounced_is_terminal(self):
        """Test BOUNCED is terminal"""
        assert MessageStatusMachine.is_terminal(MessageStatus.BOUNCED)

    def test_failed_is_terminal(self):
        """Test FAILED is terminal"""
        assert MessageStatusMachine.is_terminal(MessageStatus.FAILED)

    def test_unsubscribed_is_terminal(self):
        """Test UNSUBSCRIBED is terminal"""
        assert MessageStatusMachine.is_terminal(MessageStatus.UNSUBSCRIBED)

    def test_queued_is_not_terminal(self):
        """Test QUEUED is not terminal"""
        assert not MessageStatusMachine.is_terminal(MessageStatus.QUEUED)

    def test_sent_is_not_terminal(self):
        """Test SENT is not terminal"""
        assert not MessageStatusMachine.is_terminal(MessageStatus.SENT)

    def test_delivered_is_not_terminal(self):
        """Test DELIVERED is not terminal (can still get opens/clicks)"""
        assert not MessageStatusMachine.is_terminal(MessageStatus.DELIVERED)

    def test_opened_is_not_terminal(self):
        """Test OPENED is not terminal (can still get clicks)"""
        assert not MessageStatusMachine.is_terminal(MessageStatus.OPENED)


# ====================
# Delivery State Tests
# ====================


class TestDeliveryStates:
    """Tests for delivery state identification"""

    def test_delivered_is_delivered(self):
        """Test DELIVERED counts as delivered"""
        assert MessageStatusMachine.is_delivered(MessageStatus.DELIVERED)

    def test_opened_is_delivered(self):
        """Test OPENED counts as delivered"""
        assert MessageStatusMachine.is_delivered(MessageStatus.OPENED)

    def test_clicked_is_delivered(self):
        """Test CLICKED counts as delivered"""
        assert MessageStatusMachine.is_delivered(MessageStatus.CLICKED)

    def test_queued_is_not_delivered(self):
        """Test QUEUED is not delivered"""
        assert not MessageStatusMachine.is_delivered(MessageStatus.QUEUED)

    def test_sent_is_not_delivered(self):
        """Test SENT is not delivered (pending confirmation)"""
        assert not MessageStatusMachine.is_delivered(MessageStatus.SENT)

    def test_bounced_is_not_delivered(self):
        """Test BOUNCED is not delivered"""
        assert not MessageStatusMachine.is_delivered(MessageStatus.BOUNCED)

    def test_failed_is_not_delivered(self):
        """Test FAILED is not delivered"""
        assert not MessageStatusMachine.is_delivered(MessageStatus.FAILED)


# ====================
# Engagement State Tests
# ====================


class TestEngagementStates:
    """Tests for engagement state identification - BR-CAM-005"""

    def test_opened_is_engagement(self):
        """Test OPENED is engagement"""
        assert MessageStatusMachine.is_engagement(MessageStatus.OPENED)

    def test_clicked_is_engagement(self):
        """Test CLICKED is engagement"""
        assert MessageStatusMachine.is_engagement(MessageStatus.CLICKED)

    def test_delivered_is_not_engagement(self):
        """Test DELIVERED alone is not engagement"""
        assert not MessageStatusMachine.is_engagement(MessageStatus.DELIVERED)

    def test_queued_is_not_engagement(self):
        """Test QUEUED is not engagement"""
        assert not MessageStatusMachine.is_engagement(MessageStatus.QUEUED)


# ====================
# Failure State Tests
# ====================


class TestFailureStates:
    """Tests for failure state identification"""

    def test_bounced_is_failure(self):
        """Test BOUNCED is failure"""
        assert MessageStatusMachine.is_failure(MessageStatus.BOUNCED)

    def test_failed_is_failure(self):
        """Test FAILED is failure"""
        assert MessageStatusMachine.is_failure(MessageStatus.FAILED)

    def test_sent_is_not_failure(self):
        """Test SENT is not failure"""
        assert not MessageStatusMachine.is_failure(MessageStatus.SENT)

    def test_delivered_is_not_failure(self):
        """Test DELIVERED is not failure"""
        assert not MessageStatusMachine.is_failure(MessageStatus.DELIVERED)


# ====================
# Timestamp Field Tests
# ====================


class TestTimestampFields:
    """Tests for timestamp field mapping - BR-CAM-005.1"""

    def test_queued_timestamp_field(self):
        """Test QUEUED uses queued_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.QUEUED) == "queued_at"

    def test_sent_timestamp_field(self):
        """Test SENT uses sent_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.SENT) == "sent_at"

    def test_delivered_timestamp_field(self):
        """Test DELIVERED uses delivered_at"""
        assert (
            MessageStatusMachine.get_timestamp_field(MessageStatus.DELIVERED)
            == "delivered_at"
        )

    def test_opened_timestamp_field(self):
        """Test OPENED uses opened_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.OPENED) == "opened_at"

    def test_clicked_timestamp_field(self):
        """Test CLICKED uses clicked_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.CLICKED) == "clicked_at"

    def test_bounced_timestamp_field(self):
        """Test BOUNCED uses bounced_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.BOUNCED) == "bounced_at"

    def test_failed_timestamp_field(self):
        """Test FAILED uses failed_at"""
        assert MessageStatusMachine.get_timestamp_field(MessageStatus.FAILED) == "failed_at"

    def test_unsubscribed_timestamp_field(self):
        """Test UNSUBSCRIBED uses unsubscribed_at"""
        assert (
            MessageStatusMachine.get_timestamp_field(MessageStatus.UNSUBSCRIBED)
            == "unsubscribed_at"
        )


# ====================
# Bounce Type Tests
# ====================


class TestBounceTypes:
    """Tests for BounceType enum"""

    def test_hard_bounce(self):
        """Test hard bounce type (permanent failure)"""
        assert BounceType.HARD.value == "hard"

    def test_soft_bounce(self):
        """Test soft bounce type (temporary failure)"""
        assert BounceType.SOFT.value == "soft"


# ====================
# Parametrized Tests
# ====================


class TestAllMessageTransitions:
    """Parametrized tests for comprehensive message transition coverage"""

    @pytest.mark.parametrize(
        "from_status,to_status,expected",
        [
            # Valid transitions
            (MessageStatus.QUEUED, MessageStatus.SENT, True),
            (MessageStatus.SENT, MessageStatus.DELIVERED, True),
            (MessageStatus.SENT, MessageStatus.BOUNCED, True),
            (MessageStatus.SENT, MessageStatus.FAILED, True),
            (MessageStatus.DELIVERED, MessageStatus.OPENED, True),
            (MessageStatus.DELIVERED, MessageStatus.CLICKED, True),
            (MessageStatus.DELIVERED, MessageStatus.UNSUBSCRIBED, True),
            (MessageStatus.OPENED, MessageStatus.CLICKED, True),
            # Invalid transitions
            (MessageStatus.QUEUED, MessageStatus.DELIVERED, False),
            (MessageStatus.QUEUED, MessageStatus.OPENED, False),
            (MessageStatus.SENT, MessageStatus.QUEUED, False),
            (MessageStatus.SENT, MessageStatus.OPENED, False),
            (MessageStatus.DELIVERED, MessageStatus.SENT, False),
            (MessageStatus.BOUNCED, MessageStatus.DELIVERED, False),
            (MessageStatus.FAILED, MessageStatus.SENT, False),
            (MessageStatus.CLICKED, MessageStatus.OPENED, False),
            (MessageStatus.UNSUBSCRIBED, MessageStatus.DELIVERED, False),
        ],
    )
    def test_message_transition(self, from_status, to_status, expected):
        """Test message status transition validity"""
        result = MessageStatusMachine.can_transition(from_status, to_status)
        assert (
            result == expected
        ), f"Transition {from_status} -> {to_status} should be {'valid' if expected else 'invalid'}"
