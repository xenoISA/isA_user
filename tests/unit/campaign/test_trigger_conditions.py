"""
Unit Tests for Trigger Condition Evaluation Logic

Tests trigger condition evaluation per logic_contract.md.
Reference: BR-CAM-007 (Trigger Evaluation)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    TriggerOperator,
    TriggerCondition,
    CampaignTrigger,
    CampaignTestDataFactory,
)


class TriggerConditionEvaluator:
    """
    Trigger condition evaluation implementation for testing.

    Reference: BR-CAM-007.1 (Trigger Conditions)
    """

    @staticmethod
    def evaluate_condition(condition: TriggerCondition, event_data: dict) -> bool:
        """
        Evaluate a single trigger condition against event data - BR-CAM-007.1

        Args:
            condition: Trigger condition to evaluate
            event_data: Event payload data

        Returns:
            True if condition matches
        """
        # Get value from event data (supports nested fields via dot notation)
        field_value = TriggerConditionEvaluator._get_nested_value(
            event_data, condition.field
        )

        # Handle missing field
        if field_value is None:
            if condition.operator == TriggerOperator.EXISTS:
                return False  # Field doesn't exist
            return False

        # Evaluate based on operator
        return TriggerConditionEvaluator._evaluate_operator(
            condition.operator, field_value, condition.value
        )

    @staticmethod
    def _get_nested_value(data: dict, field: str):
        """Get nested value using dot notation (e.g., 'user.subscription.plan')"""
        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    @staticmethod
    def _evaluate_operator(operator: TriggerOperator, field_value, condition_value) -> bool:
        """Evaluate operator against values"""
        if operator == TriggerOperator.EQUALS:
            return field_value == condition_value

        elif operator == TriggerOperator.NOT_EQUALS:
            return field_value != condition_value

        elif operator == TriggerOperator.CONTAINS:
            if isinstance(field_value, str) and isinstance(condition_value, str):
                return condition_value in field_value
            elif isinstance(field_value, list):
                return condition_value in field_value
            return False

        elif operator == TriggerOperator.GREATER_THAN:
            try:
                return float(field_value) > float(condition_value)
            except (TypeError, ValueError):
                return False

        elif operator == TriggerOperator.LESS_THAN:
            try:
                return float(field_value) < float(condition_value)
            except (TypeError, ValueError):
                return False

        elif operator == TriggerOperator.IN:
            if isinstance(condition_value, list):
                return field_value in condition_value
            return False

        elif operator == TriggerOperator.EXISTS:
            return field_value is not None

        return False

    @staticmethod
    def evaluate_all_conditions(
        conditions: list, event_data: dict, require_all: bool = True
    ) -> bool:
        """
        Evaluate multiple conditions with AND/OR logic - BR-CAM-007.1

        Args:
            conditions: List of TriggerCondition
            event_data: Event payload data
            require_all: True for AND, False for OR

        Returns:
            True if conditions match according to logic
        """
        if not conditions:
            return True  # No conditions = always match

        results = [
            TriggerConditionEvaluator.evaluate_condition(c, event_data)
            for c in conditions
        ]

        if require_all:
            return all(results)  # AND logic
        else:
            return any(results)  # OR logic


class TriggerEvaluator:
    """
    Full trigger evaluation including event matching, conditions, and frequency.

    Reference: BR-CAM-007.1-4
    """

    @staticmethod
    def matches_event_type(trigger: CampaignTrigger, event_type: str) -> bool:
        """Check if trigger matches event type - BR-CAM-007.1"""
        return trigger.event_type == event_type

    @staticmethod
    def evaluate_trigger(
        trigger: CampaignTrigger, event_type: str, event_data: dict
    ) -> bool:
        """
        Full trigger evaluation - BR-CAM-007.1

        Returns True if:
        1. Event type matches
        2. All conditions pass
        """
        # Check event type
        if not TriggerEvaluator.matches_event_type(trigger, event_type):
            return False

        # Check conditions
        if trigger.conditions:
            if not TriggerConditionEvaluator.evaluate_all_conditions(
                trigger.conditions, event_data, require_all=True
            ):
                return False

        return True

    @staticmethod
    def check_frequency_limit(
        trigger: CampaignTrigger,
        user_id: str,
        trigger_history: list,  # List of datetime when trigger fired for user
    ) -> bool:
        """
        Check if frequency limit allows trigger - BR-CAM-007.3

        Args:
            trigger: Trigger with frequency config
            user_id: User to check
            trigger_history: List of datetimes when trigger fired for this user

        Returns:
            True if trigger is allowed (within frequency limit)
        """
        if not trigger.frequency_limit or not trigger.frequency_window_hours:
            return True  # No frequency limit configured

        if not trigger_history:
            return True  # No history, allow trigger

        # Calculate window start
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=trigger.frequency_window_hours)

        # Count triggers in window
        triggers_in_window = sum(
            1 for t in trigger_history if t >= window_start
        )

        return triggers_in_window < trigger.frequency_limit


# ====================
# Basic Operator Tests
# ====================


class TestTriggerOperatorEquals:
    """Tests for EQUALS operator - BR-CAM-007.1"""

    def test_equals_string_match(self):
        """Test EQUALS with matching string"""
        condition = TriggerCondition(
            field="status", operator=TriggerOperator.EQUALS, value="active"
        )
        event_data = {"status": "active"}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_equals_string_no_match(self):
        """Test EQUALS with non-matching string"""
        condition = TriggerCondition(
            field="status", operator=TriggerOperator.EQUALS, value="active"
        )
        event_data = {"status": "inactive"}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_equals_number_match(self):
        """Test EQUALS with matching number"""
        condition = TriggerCondition(
            field="count", operator=TriggerOperator.EQUALS, value=5
        )
        event_data = {"count": 5}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_equals_boolean_match(self):
        """Test EQUALS with matching boolean"""
        condition = TriggerCondition(
            field="is_premium", operator=TriggerOperator.EQUALS, value=True
        )
        event_data = {"is_premium": True}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorNotEquals:
    """Tests for NOT_EQUALS operator"""

    def test_not_equals_different_values(self):
        """Test NOT_EQUALS with different values"""
        condition = TriggerCondition(
            field="status", operator=TriggerOperator.NOT_EQUALS, value="cancelled"
        )
        event_data = {"status": "active"}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_not_equals_same_values(self):
        """Test NOT_EQUALS with same values"""
        condition = TriggerCondition(
            field="status", operator=TriggerOperator.NOT_EQUALS, value="active"
        )
        event_data = {"status": "active"}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorContains:
    """Tests for CONTAINS operator"""

    def test_contains_string_in_string(self):
        """Test CONTAINS with substring"""
        condition = TriggerCondition(
            field="email", operator=TriggerOperator.CONTAINS, value="@gmail.com"
        )
        event_data = {"email": "user@gmail.com"}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_contains_string_not_in_string(self):
        """Test CONTAINS with missing substring"""
        condition = TriggerCondition(
            field="email", operator=TriggerOperator.CONTAINS, value="@gmail.com"
        )
        event_data = {"email": "user@yahoo.com"}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_contains_item_in_list(self):
        """Test CONTAINS with item in list"""
        condition = TriggerCondition(
            field="tags", operator=TriggerOperator.CONTAINS, value="premium"
        )
        event_data = {"tags": ["premium", "verified", "active"]}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_contains_item_not_in_list(self):
        """Test CONTAINS with item not in list"""
        condition = TriggerCondition(
            field="tags", operator=TriggerOperator.CONTAINS, value="premium"
        )
        event_data = {"tags": ["basic", "verified"]}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorGreaterThan:
    """Tests for GREATER_THAN operator"""

    def test_greater_than_true(self):
        """Test GREATER_THAN with larger value"""
        condition = TriggerCondition(
            field="amount", operator=TriggerOperator.GREATER_THAN, value=100
        )
        event_data = {"amount": 150}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_greater_than_false_equal(self):
        """Test GREATER_THAN with equal value"""
        condition = TriggerCondition(
            field="amount", operator=TriggerOperator.GREATER_THAN, value=100
        )
        event_data = {"amount": 100}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_greater_than_false_smaller(self):
        """Test GREATER_THAN with smaller value"""
        condition = TriggerCondition(
            field="amount", operator=TriggerOperator.GREATER_THAN, value=100
        )
        event_data = {"amount": 50}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorLessThan:
    """Tests for LESS_THAN operator"""

    def test_less_than_true(self):
        """Test LESS_THAN with smaller value"""
        condition = TriggerCondition(
            field="days_since_login", operator=TriggerOperator.LESS_THAN, value=7
        )
        event_data = {"days_since_login": 3}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_less_than_false_equal(self):
        """Test LESS_THAN with equal value"""
        condition = TriggerCondition(
            field="days_since_login", operator=TriggerOperator.LESS_THAN, value=7
        )
        event_data = {"days_since_login": 7}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_less_than_false_larger(self):
        """Test LESS_THAN with larger value"""
        condition = TriggerCondition(
            field="days_since_login", operator=TriggerOperator.LESS_THAN, value=7
        )
        event_data = {"days_since_login": 14}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorIn:
    """Tests for IN operator"""

    def test_in_value_present(self):
        """Test IN with value in list"""
        condition = TriggerCondition(
            field="country", operator=TriggerOperator.IN, value=["US", "CA", "UK"]
        )
        event_data = {"country": "US"}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_in_value_absent(self):
        """Test IN with value not in list"""
        condition = TriggerCondition(
            field="country", operator=TriggerOperator.IN, value=["US", "CA", "UK"]
        )
        event_data = {"country": "FR"}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


class TestTriggerOperatorExists:
    """Tests for EXISTS operator"""

    def test_exists_field_present(self):
        """Test EXISTS with field present"""
        condition = TriggerCondition(
            field="phone", operator=TriggerOperator.EXISTS, value=None
        )
        event_data = {"phone": "+1234567890"}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_exists_field_absent(self):
        """Test EXISTS with field absent"""
        condition = TriggerCondition(
            field="phone", operator=TriggerOperator.EXISTS, value=None
        )
        event_data = {"email": "user@example.com"}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_exists_field_null(self):
        """Test EXISTS with null value (field present but null)"""
        condition = TriggerCondition(
            field="phone", operator=TriggerOperator.EXISTS, value=None
        )
        event_data = {"phone": None}
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


# ====================
# Nested Field Tests
# ====================


class TestNestedFieldAccess:
    """Tests for nested field access in conditions"""

    def test_nested_one_level(self):
        """Test single level nesting"""
        condition = TriggerCondition(
            field="user.plan", operator=TriggerOperator.EQUALS, value="premium"
        )
        event_data = {"user": {"plan": "premium"}}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_nested_two_levels(self):
        """Test two level nesting"""
        condition = TriggerCondition(
            field="user.subscription.tier",
            operator=TriggerOperator.EQUALS,
            value="gold",
        )
        event_data = {"user": {"subscription": {"tier": "gold"}}}
        assert TriggerConditionEvaluator.evaluate_condition(condition, event_data)

    def test_nested_missing_intermediate(self):
        """Test missing intermediate field"""
        condition = TriggerCondition(
            field="user.subscription.tier",
            operator=TriggerOperator.EQUALS,
            value="gold",
        )
        event_data = {"user": {"name": "John"}}  # No subscription
        assert not TriggerConditionEvaluator.evaluate_condition(condition, event_data)


# ====================
# Multiple Conditions Tests
# ====================


class TestMultipleConditions:
    """Tests for multiple conditions with AND/OR logic - BR-CAM-007.1"""

    def test_all_conditions_and_all_match(self):
        """Test AND logic with all matching"""
        conditions = [
            TriggerCondition(
                field="status", operator=TriggerOperator.EQUALS, value="active"
            ),
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="premium"
            ),
        ]
        event_data = {"status": "active", "plan": "premium"}
        assert TriggerConditionEvaluator.evaluate_all_conditions(
            conditions, event_data, require_all=True
        )

    def test_all_conditions_and_one_fails(self):
        """Test AND logic with one failing"""
        conditions = [
            TriggerCondition(
                field="status", operator=TriggerOperator.EQUALS, value="active"
            ),
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="premium"
            ),
        ]
        event_data = {"status": "active", "plan": "basic"}
        assert not TriggerConditionEvaluator.evaluate_all_conditions(
            conditions, event_data, require_all=True
        )

    def test_any_conditions_or_one_matches(self):
        """Test OR logic with one matching"""
        conditions = [
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="premium"
            ),
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="enterprise"
            ),
        ]
        event_data = {"plan": "premium"}
        assert TriggerConditionEvaluator.evaluate_all_conditions(
            conditions, event_data, require_all=False
        )

    def test_any_conditions_or_none_match(self):
        """Test OR logic with none matching"""
        conditions = [
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="premium"
            ),
            TriggerCondition(
                field="plan", operator=TriggerOperator.EQUALS, value="enterprise"
            ),
        ]
        event_data = {"plan": "basic"}
        assert not TriggerConditionEvaluator.evaluate_all_conditions(
            conditions, event_data, require_all=False
        )

    def test_empty_conditions_always_match(self):
        """Test empty conditions list always matches"""
        assert TriggerConditionEvaluator.evaluate_all_conditions(
            [], {"any": "data"}, require_all=True
        )


# ====================
# Trigger Evaluation Tests
# ====================


class TestTriggerEvaluation:
    """Tests for full trigger evaluation - BR-CAM-007.1"""

    def test_trigger_matches_event_type(self, factory):
        """Test trigger matches correct event type"""
        trigger = factory.make_trigger(event_type="user.purchase")
        assert TriggerEvaluator.matches_event_type(trigger, "user.purchase")

    def test_trigger_does_not_match_wrong_event(self, factory):
        """Test trigger doesn't match wrong event type"""
        trigger = factory.make_trigger(event_type="user.purchase")
        assert not TriggerEvaluator.matches_event_type(trigger, "user.login")

    def test_trigger_full_evaluation_pass(self, factory):
        """Test full trigger evaluation with matching event and conditions"""
        trigger = factory.make_trigger(event_type="order.completed")
        trigger.conditions = [
            TriggerCondition(
                field="total", operator=TriggerOperator.GREATER_THAN, value=100
            )
        ]

        event_data = {"total": 150, "user_id": "usr_123"}
        assert TriggerEvaluator.evaluate_trigger(trigger, "order.completed", event_data)

    def test_trigger_full_evaluation_fail_conditions(self, factory):
        """Test full trigger evaluation failing conditions"""
        trigger = factory.make_trigger(event_type="order.completed")
        trigger.conditions = [
            TriggerCondition(
                field="total", operator=TriggerOperator.GREATER_THAN, value=100
            )
        ]

        event_data = {"total": 50, "user_id": "usr_123"}
        assert not TriggerEvaluator.evaluate_trigger(
            trigger, "order.completed", event_data
        )


# ====================
# Frequency Limit Tests
# ====================


class TestFrequencyLimit:
    """Tests for frequency limit checking - BR-CAM-007.3"""

    def test_no_frequency_limit_always_allowed(self, factory):
        """Test no frequency limit allows all triggers"""
        trigger = factory.make_trigger(event_type="user.action")
        trigger.frequency_limit = None
        trigger.frequency_window_hours = None

        history = [datetime.now(timezone.utc) for _ in range(10)]
        assert TriggerEvaluator.check_frequency_limit(trigger, "usr_123", history)

    def test_within_frequency_limit(self, factory):
        """Test trigger allowed within frequency limit"""
        trigger = factory.make_trigger(event_type="user.action")
        trigger.frequency_limit = 3
        trigger.frequency_window_hours = 24

        # 2 triggers in last 24 hours, limit is 3
        now = datetime.now(timezone.utc)
        history = [
            now - timedelta(hours=12),
            now - timedelta(hours=6),
        ]
        assert TriggerEvaluator.check_frequency_limit(trigger, "usr_123", history)

    def test_at_frequency_limit(self, factory):
        """Test trigger blocked at frequency limit"""
        trigger = factory.make_trigger(event_type="user.action")
        trigger.frequency_limit = 3
        trigger.frequency_window_hours = 24

        # 3 triggers in last 24 hours, limit is 3
        now = datetime.now(timezone.utc)
        history = [
            now - timedelta(hours=18),
            now - timedelta(hours=12),
            now - timedelta(hours=6),
        ]
        assert not TriggerEvaluator.check_frequency_limit(trigger, "usr_123", history)

    def test_old_history_outside_window(self, factory):
        """Test old triggers outside window don't count"""
        trigger = factory.make_trigger(event_type="user.action")
        trigger.frequency_limit = 1
        trigger.frequency_window_hours = 24

        # 1 trigger but outside 24h window
        now = datetime.now(timezone.utc)
        history = [now - timedelta(hours=30)]
        assert TriggerEvaluator.check_frequency_limit(trigger, "usr_123", history)


# ====================
# Parametrized Tests
# ====================


class TestTriggerConditionsParametrized:
    """Parametrized trigger condition tests"""

    @pytest.mark.parametrize(
        "operator,field_value,condition_value,expected",
        [
            (TriggerOperator.EQUALS, "active", "active", True),
            (TriggerOperator.EQUALS, "active", "inactive", False),
            (TriggerOperator.NOT_EQUALS, "active", "inactive", True),
            (TriggerOperator.NOT_EQUALS, "active", "active", False),
            (TriggerOperator.GREATER_THAN, 150, 100, True),
            (TriggerOperator.GREATER_THAN, 100, 100, False),
            (TriggerOperator.LESS_THAN, 50, 100, True),
            (TriggerOperator.LESS_THAN, 100, 100, False),
            (TriggerOperator.IN, "US", ["US", "CA"], True),
            (TriggerOperator.IN, "FR", ["US", "CA"], False),
            (TriggerOperator.CONTAINS, "hello world", "world", True),
            (TriggerOperator.CONTAINS, "hello world", "foo", False),
        ],
    )
    def test_operator_evaluation(
        self, operator, field_value, condition_value, expected
    ):
        """Test various operator evaluations"""
        condition = TriggerCondition(
            field="test_field", operator=operator, value=condition_value
        )
        event_data = {"test_field": field_value}
        result = TriggerConditionEvaluator.evaluate_condition(condition, event_data)
        assert result == expected
