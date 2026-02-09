"""
Unit Tests for Execution Status State Machine

Tests all valid and invalid execution status transitions per logic_contract.md.
Reference: Execution Status State Machine
"""

import pytest
from datetime import datetime, timezone

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    ExecutionStatus,
    ExecutionType,
    CampaignTestDataFactory,
)


class ExecutionStatusMachine:
    """
    Execution Status State Machine implementation for testing.

    Valid Transitions:
    - PENDING -> RUNNING (execution starts)
    - RUNNING -> PAUSED (user pauses)
    - RUNNING -> COMPLETED (all messages processed)
    - RUNNING -> FAILED (critical error)
    - RUNNING -> CANCELLED (user cancels)
    - PAUSED -> RUNNING (user resumes)
    - PAUSED -> CANCELLED (user cancels while paused)
    """

    VALID_TRANSITIONS = {
        ExecutionStatus.PENDING: {ExecutionStatus.RUNNING},
        ExecutionStatus.RUNNING: {
            ExecutionStatus.PAUSED,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.PAUSED: {
            ExecutionStatus.RUNNING,
            ExecutionStatus.CANCELLED,
        },
        # Terminal states
        ExecutionStatus.COMPLETED: set(),
        ExecutionStatus.FAILED: set(),
        ExecutionStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(
        cls, from_status: ExecutionStatus, to_status: ExecutionStatus
    ) -> bool:
        """Check if transition is valid"""
        valid_targets = cls.VALID_TRANSITIONS.get(from_status, set())
        return to_status in valid_targets

    @classmethod
    def is_terminal(cls, status: ExecutionStatus) -> bool:
        """Check if status is terminal (execution finished)"""
        return status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }

    @classmethod
    def is_active(cls, status: ExecutionStatus) -> bool:
        """Check if execution is actively processing"""
        return status == ExecutionStatus.RUNNING

    @classmethod
    def is_success(cls, status: ExecutionStatus) -> bool:
        """Check if execution completed successfully"""
        return status == ExecutionStatus.COMPLETED


# ====================
# Valid Transition Tests
# ====================


class TestValidExecutionStatusTransitions:
    """Tests for valid execution status transitions"""

    def test_pending_to_running_valid(self):
        """Test PENDING -> RUNNING is valid (execution starts)"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.RUNNING
        )

    def test_running_to_paused_valid(self):
        """Test RUNNING -> PAUSED is valid"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.PAUSED
        )

    def test_running_to_completed_valid(self):
        """Test RUNNING -> COMPLETED is valid"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED
        )

    def test_running_to_failed_valid(self):
        """Test RUNNING -> FAILED is valid (critical error)"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.FAILED
        )

    def test_running_to_cancelled_valid(self):
        """Test RUNNING -> CANCELLED is valid"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED
        )

    def test_paused_to_running_valid(self):
        """Test PAUSED -> RUNNING is valid (resume)"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.PAUSED, ExecutionStatus.RUNNING
        )

    def test_paused_to_cancelled_valid(self):
        """Test PAUSED -> CANCELLED is valid"""
        assert ExecutionStatusMachine.can_transition(
            ExecutionStatus.PAUSED, ExecutionStatus.CANCELLED
        )


# ====================
# Invalid Transition Tests
# ====================


class TestInvalidExecutionStatusTransitions:
    """Tests for invalid execution status transitions"""

    def test_pending_to_paused_invalid(self):
        """Test PENDING -> PAUSED is invalid (can't pause before starting)"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.PAUSED
        )

    def test_pending_to_completed_invalid(self):
        """Test PENDING -> COMPLETED is invalid (must run first)"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.COMPLETED
        )

    def test_pending_to_failed_invalid(self):
        """Test PENDING -> FAILED is invalid (must start first)"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.FAILED
        )

    def test_pending_to_cancelled_invalid(self):
        """Test PENDING -> CANCELLED is invalid (must start first)"""
        # Note: In some systems you might want to allow this
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PENDING, ExecutionStatus.CANCELLED
        )

    def test_paused_to_completed_invalid(self):
        """Test PAUSED -> COMPLETED is invalid (must resume and finish)"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PAUSED, ExecutionStatus.COMPLETED
        )

    def test_paused_to_failed_invalid(self):
        """Test PAUSED -> FAILED is invalid"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.PAUSED, ExecutionStatus.FAILED
        )

    def test_completed_to_any_invalid(self):
        """Test COMPLETED -> any is invalid (terminal state)"""
        for status in ExecutionStatus:
            if status != ExecutionStatus.COMPLETED:
                assert not ExecutionStatusMachine.can_transition(
                    ExecutionStatus.COMPLETED, status
                ), f"COMPLETED -> {status} should be invalid"

    def test_failed_to_any_invalid(self):
        """Test FAILED -> any is invalid (terminal state)"""
        for status in ExecutionStatus:
            if status != ExecutionStatus.FAILED:
                assert not ExecutionStatusMachine.can_transition(
                    ExecutionStatus.FAILED, status
                ), f"FAILED -> {status} should be invalid"

    def test_cancelled_to_any_invalid(self):
        """Test CANCELLED -> any is invalid (terminal state)"""
        for status in ExecutionStatus:
            if status != ExecutionStatus.CANCELLED:
                assert not ExecutionStatusMachine.can_transition(
                    ExecutionStatus.CANCELLED, status
                ), f"CANCELLED -> {status} should be invalid"

    def test_reverse_transitions_invalid(self):
        """Test reverse transitions are invalid"""
        assert not ExecutionStatusMachine.can_transition(
            ExecutionStatus.RUNNING, ExecutionStatus.PENDING
        )


# ====================
# Terminal State Tests
# ====================


class TestTerminalExecutionStates:
    """Tests for terminal execution state identification"""

    def test_completed_is_terminal(self):
        """Test COMPLETED is terminal"""
        assert ExecutionStatusMachine.is_terminal(ExecutionStatus.COMPLETED)

    def test_failed_is_terminal(self):
        """Test FAILED is terminal"""
        assert ExecutionStatusMachine.is_terminal(ExecutionStatus.FAILED)

    def test_cancelled_is_terminal(self):
        """Test CANCELLED is terminal"""
        assert ExecutionStatusMachine.is_terminal(ExecutionStatus.CANCELLED)

    def test_pending_is_not_terminal(self):
        """Test PENDING is not terminal"""
        assert not ExecutionStatusMachine.is_terminal(ExecutionStatus.PENDING)

    def test_running_is_not_terminal(self):
        """Test RUNNING is not terminal"""
        assert not ExecutionStatusMachine.is_terminal(ExecutionStatus.RUNNING)

    def test_paused_is_not_terminal(self):
        """Test PAUSED is not terminal"""
        assert not ExecutionStatusMachine.is_terminal(ExecutionStatus.PAUSED)


# ====================
# Active State Tests
# ====================


class TestActiveExecutionStates:
    """Tests for active execution state identification"""

    def test_running_is_active(self):
        """Test RUNNING is active"""
        assert ExecutionStatusMachine.is_active(ExecutionStatus.RUNNING)

    def test_pending_is_not_active(self):
        """Test PENDING is not active"""
        assert not ExecutionStatusMachine.is_active(ExecutionStatus.PENDING)

    def test_paused_is_not_active(self):
        """Test PAUSED is not active (not processing)"""
        assert not ExecutionStatusMachine.is_active(ExecutionStatus.PAUSED)

    def test_completed_is_not_active(self):
        """Test COMPLETED is not active"""
        assert not ExecutionStatusMachine.is_active(ExecutionStatus.COMPLETED)


# ====================
# Success State Tests
# ====================


class TestSuccessExecutionStates:
    """Tests for success state identification"""

    def test_completed_is_success(self):
        """Test COMPLETED is success"""
        assert ExecutionStatusMachine.is_success(ExecutionStatus.COMPLETED)

    def test_failed_is_not_success(self):
        """Test FAILED is not success"""
        assert not ExecutionStatusMachine.is_success(ExecutionStatus.FAILED)

    def test_cancelled_is_not_success(self):
        """Test CANCELLED is not success"""
        assert not ExecutionStatusMachine.is_success(ExecutionStatus.CANCELLED)

    def test_running_is_not_success(self):
        """Test RUNNING is not success (still in progress)"""
        assert not ExecutionStatusMachine.is_success(ExecutionStatus.RUNNING)


# ====================
# Execution Type Tests
# ====================


class TestExecutionTypes:
    """Tests for ExecutionType enum"""

    def test_scheduled_type(self):
        """Test scheduled execution type"""
        assert ExecutionType.SCHEDULED.value == "scheduled"

    def test_triggered_type(self):
        """Test triggered execution type"""
        assert ExecutionType.TRIGGERED.value == "triggered"

    def test_manual_type(self):
        """Test manual execution type"""
        assert ExecutionType.MANUAL.value == "manual"


# ====================
# Parametrized Tests
# ====================


class TestAllExecutionTransitions:
    """Parametrized tests for comprehensive execution transition coverage"""

    @pytest.mark.parametrize(
        "from_status,to_status,expected",
        [
            # Valid transitions
            (ExecutionStatus.PENDING, ExecutionStatus.RUNNING, True),
            (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED, True),
            (ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED, True),
            (ExecutionStatus.RUNNING, ExecutionStatus.FAILED, True),
            (ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED, True),
            (ExecutionStatus.PAUSED, ExecutionStatus.RUNNING, True),
            (ExecutionStatus.PAUSED, ExecutionStatus.CANCELLED, True),
            # Invalid transitions
            (ExecutionStatus.PENDING, ExecutionStatus.PAUSED, False),
            (ExecutionStatus.PENDING, ExecutionStatus.COMPLETED, False),
            (ExecutionStatus.PENDING, ExecutionStatus.FAILED, False),
            (ExecutionStatus.RUNNING, ExecutionStatus.PENDING, False),
            (ExecutionStatus.PAUSED, ExecutionStatus.COMPLETED, False),
            (ExecutionStatus.PAUSED, ExecutionStatus.FAILED, False),
            (ExecutionStatus.COMPLETED, ExecutionStatus.RUNNING, False),
            (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, False),
            (ExecutionStatus.FAILED, ExecutionStatus.RUNNING, False),
            (ExecutionStatus.FAILED, ExecutionStatus.COMPLETED, False),
            (ExecutionStatus.CANCELLED, ExecutionStatus.RUNNING, False),
            (ExecutionStatus.CANCELLED, ExecutionStatus.COMPLETED, False),
        ],
    )
    def test_execution_transition(self, from_status, to_status, expected):
        """Test execution status transition validity"""
        result = ExecutionStatusMachine.can_transition(from_status, to_status)
        assert (
            result == expected
        ), f"Transition {from_status} -> {to_status} should be {'valid' if expected else 'invalid'}"
