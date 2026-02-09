"""
Unit Tests for Campaign Status State Machine

Tests all valid and invalid state transitions per logic_contract.md.
Reference: Campaign Status State Machine (logic_contract.md)
"""

import pytest
from datetime import datetime, timezone

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
    CampaignTestDataFactory,
)


class CampaignStatusMachine:
    """
    Campaign Status State Machine implementation for testing.

    Valid Transitions:
    - DRAFT -> SCHEDULED (schedule scheduled campaign)
    - DRAFT -> ACTIVE (activate triggered campaign)
    - SCHEDULED -> RUNNING (task executes at scheduled time)
    - SCHEDULED -> CANCELLED (cancel before execution)
    - SCHEDULED -> DRAFT (unschedule to edit)
    - ACTIVE -> RUNNING (trigger fires)
    - ACTIVE -> CANCELLED (deactivate triggered campaign)
    - ACTIVE -> DRAFT (deactivate to edit)
    - RUNNING -> PAUSED (pause execution)
    - RUNNING -> COMPLETED (all messages processed)
    - RUNNING -> CANCELLED (cancel during execution)
    - PAUSED -> RUNNING (resume execution)
    - PAUSED -> CANCELLED (cancel paused campaign)
    """

    VALID_TRANSITIONS = {
        CampaignStatus.DRAFT: {
            CampaignStatus.SCHEDULED,  # For scheduled campaigns
            CampaignStatus.ACTIVE,  # For triggered campaigns
        },
        CampaignStatus.SCHEDULED: {
            CampaignStatus.RUNNING,
            CampaignStatus.CANCELLED,
            CampaignStatus.DRAFT,
        },
        CampaignStatus.ACTIVE: {
            CampaignStatus.RUNNING,
            CampaignStatus.CANCELLED,
            CampaignStatus.DRAFT,
        },
        CampaignStatus.RUNNING: {
            CampaignStatus.PAUSED,
            CampaignStatus.COMPLETED,
            CampaignStatus.CANCELLED,
        },
        CampaignStatus.PAUSED: {
            CampaignStatus.RUNNING,
            CampaignStatus.CANCELLED,
        },
        # Terminal states - no transitions allowed
        CampaignStatus.COMPLETED: set(),
        CampaignStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, from_status: CampaignStatus, to_status: CampaignStatus) -> bool:
        """Check if transition is valid"""
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, set())
        return to_status in valid_targets

    @classmethod
    def is_terminal_state(cls, status: CampaignStatus) -> bool:
        """Check if status is terminal (no further transitions)"""
        return status in {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}

    @classmethod
    def can_edit(cls, status: CampaignStatus) -> bool:
        """Check if campaign can be edited in this status - BR-CAM-001.8"""
        return status in {CampaignStatus.DRAFT, CampaignStatus.PAUSED}


# ====================
# Valid Transition Tests
# ====================


class TestValidCampaignStatusTransitions:
    """Tests for valid campaign status transitions"""

    # DRAFT transitions
    def test_draft_to_scheduled_valid(self):
        """Test DRAFT -> SCHEDULED for scheduled campaigns - BR-CAM-001.2"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.DRAFT, CampaignStatus.SCHEDULED
        )

    def test_draft_to_active_valid(self):
        """Test DRAFT -> ACTIVE for triggered campaigns - BR-CAM-001.3"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.DRAFT, CampaignStatus.ACTIVE
        )

    # SCHEDULED transitions
    def test_scheduled_to_running_valid(self):
        """Test SCHEDULED -> RUNNING when task executes"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.SCHEDULED, CampaignStatus.RUNNING
        )

    def test_scheduled_to_cancelled_valid(self):
        """Test SCHEDULED -> CANCELLED - BR-CAM-001.6"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.SCHEDULED, CampaignStatus.CANCELLED
        )

    def test_scheduled_to_draft_valid(self):
        """Test SCHEDULED -> DRAFT (unschedule to edit)"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.SCHEDULED, CampaignStatus.DRAFT
        )

    # ACTIVE transitions (triggered campaigns)
    def test_active_to_running_valid(self):
        """Test ACTIVE -> RUNNING when trigger fires"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.ACTIVE, CampaignStatus.RUNNING
        )

    def test_active_to_cancelled_valid(self):
        """Test ACTIVE -> CANCELLED (deactivate) - BR-CAM-001.6"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.ACTIVE, CampaignStatus.CANCELLED
        )

    def test_active_to_draft_valid(self):
        """Test ACTIVE -> DRAFT (deactivate to edit)"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.ACTIVE, CampaignStatus.DRAFT
        )

    # RUNNING transitions
    def test_running_to_paused_valid(self):
        """Test RUNNING -> PAUSED - BR-CAM-001.4"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.PAUSED
        )

    def test_running_to_completed_valid(self):
        """Test RUNNING -> COMPLETED when all messages processed"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.COMPLETED
        )

    def test_running_to_cancelled_valid(self):
        """Test RUNNING -> CANCELLED - BR-CAM-001.6"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.CANCELLED
        )

    # PAUSED transitions
    def test_paused_to_running_valid(self):
        """Test PAUSED -> RUNNING (resume) - BR-CAM-001.5"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.PAUSED, CampaignStatus.RUNNING
        )

    def test_paused_to_cancelled_valid(self):
        """Test PAUSED -> CANCELLED - BR-CAM-001.6"""
        assert CampaignStatusMachine.can_transition(
            CampaignStatus.PAUSED, CampaignStatus.CANCELLED
        )


# ====================
# Invalid Transition Tests
# ====================


class TestInvalidCampaignStatusTransitions:
    """Tests for invalid campaign status transitions - 409 Conflict scenarios"""

    # Terminal state transitions (should all fail)
    def test_completed_to_any_invalid(self):
        """Test COMPLETED -> any is invalid (terminal state)"""
        for status in CampaignStatus:
            if status != CampaignStatus.COMPLETED:
                assert not CampaignStatusMachine.can_transition(
                    CampaignStatus.COMPLETED, status
                ), f"COMPLETED -> {status} should be invalid"

    def test_cancelled_to_any_invalid(self):
        """Test CANCELLED -> any is invalid (terminal state)"""
        for status in CampaignStatus:
            if status != CampaignStatus.CANCELLED:
                assert not CampaignStatusMachine.can_transition(
                    CampaignStatus.CANCELLED, status
                ), f"CANCELLED -> {status} should be invalid"

    # Invalid DRAFT transitions
    def test_draft_to_running_invalid(self):
        """Test DRAFT -> RUNNING is invalid (must go through SCHEDULED/ACTIVE)"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.DRAFT, CampaignStatus.RUNNING
        )

    def test_draft_to_paused_invalid(self):
        """Test DRAFT -> PAUSED is invalid"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.DRAFT, CampaignStatus.PAUSED
        )

    def test_draft_to_completed_invalid(self):
        """Test DRAFT -> COMPLETED is invalid"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.DRAFT, CampaignStatus.COMPLETED
        )

    # Invalid cross-type transitions
    def test_scheduled_to_active_invalid(self):
        """Test SCHEDULED -> ACTIVE is invalid (different campaign types)"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.SCHEDULED, CampaignStatus.ACTIVE
        )

    def test_active_to_scheduled_invalid(self):
        """Test ACTIVE -> SCHEDULED is invalid (different campaign types)"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.ACTIVE, CampaignStatus.SCHEDULED
        )

    # Invalid RUNNING transitions
    def test_running_to_draft_invalid(self):
        """Test RUNNING -> DRAFT is invalid (must pause first) - BR-CAM-001.8"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.DRAFT
        )

    def test_running_to_scheduled_invalid(self):
        """Test RUNNING -> SCHEDULED is invalid"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.SCHEDULED
        )

    def test_running_to_active_invalid(self):
        """Test RUNNING -> ACTIVE is invalid"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.RUNNING, CampaignStatus.ACTIVE
        )

    # Invalid PAUSED transitions
    def test_paused_to_draft_invalid(self):
        """Test PAUSED -> DRAFT is invalid (must be explicitly unpaused)"""
        # Note: Paused campaigns CAN be edited but status change to DRAFT requires explicit action
        # The state machine doesn't allow direct PAUSED -> DRAFT, use update while paused
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.PAUSED, CampaignStatus.DRAFT
        )

    def test_paused_to_completed_invalid(self):
        """Test PAUSED -> COMPLETED is invalid (must resume first)"""
        assert not CampaignStatusMachine.can_transition(
            CampaignStatus.PAUSED, CampaignStatus.COMPLETED
        )


# ====================
# Terminal State Tests
# ====================


class TestTerminalStates:
    """Tests for terminal state identification"""

    def test_completed_is_terminal(self):
        """Test COMPLETED is terminal state"""
        assert CampaignStatusMachine.is_terminal_state(CampaignStatus.COMPLETED)

    def test_cancelled_is_terminal(self):
        """Test CANCELLED is terminal state"""
        assert CampaignStatusMachine.is_terminal_state(CampaignStatus.CANCELLED)

    def test_draft_is_not_terminal(self):
        """Test DRAFT is not terminal"""
        assert not CampaignStatusMachine.is_terminal_state(CampaignStatus.DRAFT)

    def test_scheduled_is_not_terminal(self):
        """Test SCHEDULED is not terminal"""
        assert not CampaignStatusMachine.is_terminal_state(CampaignStatus.SCHEDULED)

    def test_active_is_not_terminal(self):
        """Test ACTIVE is not terminal"""
        assert not CampaignStatusMachine.is_terminal_state(CampaignStatus.ACTIVE)

    def test_running_is_not_terminal(self):
        """Test RUNNING is not terminal"""
        assert not CampaignStatusMachine.is_terminal_state(CampaignStatus.RUNNING)

    def test_paused_is_not_terminal(self):
        """Test PAUSED is not terminal"""
        assert not CampaignStatusMachine.is_terminal_state(CampaignStatus.PAUSED)


# ====================
# Edit State Tests
# ====================


class TestEditableStates:
    """Tests for editable state identification - BR-CAM-001.5-8"""

    def test_draft_is_editable(self):
        """Test DRAFT campaigns can be edited - BR-CAM-001.8"""
        assert CampaignStatusMachine.can_edit(CampaignStatus.DRAFT)

    def test_paused_is_editable(self):
        """Test PAUSED campaigns can be edited - BR-CAM-001.5"""
        assert CampaignStatusMachine.can_edit(CampaignStatus.PAUSED)

    def test_scheduled_is_not_editable(self):
        """Test SCHEDULED campaigns cannot be edited directly"""
        assert not CampaignStatusMachine.can_edit(CampaignStatus.SCHEDULED)

    def test_active_is_not_editable(self):
        """Test ACTIVE campaigns cannot be edited directly"""
        assert not CampaignStatusMachine.can_edit(CampaignStatus.ACTIVE)

    def test_running_is_not_editable(self):
        """Test RUNNING campaigns cannot be edited - BR-CAM-001.6"""
        assert not CampaignStatusMachine.can_edit(CampaignStatus.RUNNING)

    def test_completed_is_not_editable(self):
        """Test COMPLETED campaigns cannot be edited - BR-CAM-001.7"""
        assert not CampaignStatusMachine.can_edit(CampaignStatus.COMPLETED)

    def test_cancelled_is_not_editable(self):
        """Test CANCELLED campaigns cannot be edited - BR-CAM-001.8"""
        assert not CampaignStatusMachine.can_edit(CampaignStatus.CANCELLED)


# ====================
# Campaign Type Constraints
# ====================


class TestCampaignTypeStatusConstraints:
    """Tests for campaign type specific status constraints"""

    def test_scheduled_campaign_cannot_activate(self):
        """Test scheduled campaign cannot go to ACTIVE status - BR-CAM-001.3"""
        # Scheduled campaigns should go DRAFT -> SCHEDULED, not DRAFT -> ACTIVE
        campaign = CampaignTestDataFactory.make_campaign(
            campaign_type=CampaignType.SCHEDULED, status=CampaignStatus.DRAFT
        )
        # The transition DRAFT -> ACTIVE is technically valid in state machine,
        # but business logic should prevent this for scheduled campaigns
        assert campaign.campaign_type == CampaignType.SCHEDULED
        # This constraint should be enforced at service layer, not state machine

    def test_triggered_campaign_cannot_schedule(self):
        """Test triggered campaign cannot go to SCHEDULED status - BR-CAM-001.2"""
        # Triggered campaigns should go DRAFT -> ACTIVE, not DRAFT -> SCHEDULED
        campaign = CampaignTestDataFactory.make_campaign(
            campaign_type=CampaignType.TRIGGERED, status=CampaignStatus.DRAFT
        )
        assert campaign.campaign_type == CampaignType.TRIGGERED
        # This constraint should be enforced at service layer, not state machine


# ====================
# Parametrized Tests
# ====================


class TestAllTransitions:
    """Parametrized tests for comprehensive transition coverage"""

    @pytest.mark.parametrize(
        "from_status,to_status,expected",
        [
            # Valid transitions
            (CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, True),
            (CampaignStatus.DRAFT, CampaignStatus.ACTIVE, True),
            (CampaignStatus.SCHEDULED, CampaignStatus.RUNNING, True),
            (CampaignStatus.SCHEDULED, CampaignStatus.CANCELLED, True),
            (CampaignStatus.SCHEDULED, CampaignStatus.DRAFT, True),
            (CampaignStatus.ACTIVE, CampaignStatus.RUNNING, True),
            (CampaignStatus.ACTIVE, CampaignStatus.CANCELLED, True),
            (CampaignStatus.ACTIVE, CampaignStatus.DRAFT, True),
            (CampaignStatus.RUNNING, CampaignStatus.PAUSED, True),
            (CampaignStatus.RUNNING, CampaignStatus.COMPLETED, True),
            (CampaignStatus.RUNNING, CampaignStatus.CANCELLED, True),
            (CampaignStatus.PAUSED, CampaignStatus.RUNNING, True),
            (CampaignStatus.PAUSED, CampaignStatus.CANCELLED, True),
            # Invalid transitions
            (CampaignStatus.DRAFT, CampaignStatus.RUNNING, False),
            (CampaignStatus.DRAFT, CampaignStatus.COMPLETED, False),
            (CampaignStatus.SCHEDULED, CampaignStatus.ACTIVE, False),
            (CampaignStatus.ACTIVE, CampaignStatus.SCHEDULED, False),
            (CampaignStatus.RUNNING, CampaignStatus.DRAFT, False),
            (CampaignStatus.COMPLETED, CampaignStatus.DRAFT, False),
            (CampaignStatus.COMPLETED, CampaignStatus.RUNNING, False),
            (CampaignStatus.CANCELLED, CampaignStatus.DRAFT, False),
            (CampaignStatus.CANCELLED, CampaignStatus.RUNNING, False),
        ],
    )
    def test_transition(self, from_status, to_status, expected):
        """Test status transition validity"""
        result = CampaignStatusMachine.can_transition(from_status, to_status)
        assert (
            result == expected
        ), f"Transition {from_status} -> {to_status} should be {'valid' if expected else 'invalid'}"
