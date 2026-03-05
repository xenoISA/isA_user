"""
L1 Unit Tests — Tax Service Logic

Tests pure functions and static methods with no I/O.
"""

import pytest
from microservices.tax_service.tax_service import TaxService
from microservices.tax_service.events.models import TaxLineItem


@pytest.mark.unit
class TestComputeSubtotal:
    """Test TaxService._compute_subtotal static helper"""

    def test_computes_from_unit_price_and_quantity(self):
        items = [{"unit_price": 10.0, "quantity": 3}]
        assert TaxService._compute_subtotal(items) == 30.0

    def test_computes_from_amount_field(self):
        items = [{"amount": 25.0}]
        assert TaxService._compute_subtotal(items) == 25.0

    def test_amount_takes_priority_over_unit_price(self):
        items = [{"amount": 50.0, "unit_price": 10.0, "quantity": 3}]
        assert TaxService._compute_subtotal(items) == 50.0

    def test_defaults_unit_price_to_zero(self):
        items = [{"quantity": 5}]
        assert TaxService._compute_subtotal(items) == 0

    def test_defaults_quantity_to_one(self):
        items = [{"unit_price": 7.0}]
        assert TaxService._compute_subtotal(items) == 7.0

    def test_empty_items_returns_zero(self):
        assert TaxService._compute_subtotal([]) == 0

    def test_multiple_items_summed(self):
        items = [
            {"unit_price": 10.0, "quantity": 2},
            {"unit_price": 5.0, "quantity": 3},
        ]
        assert TaxService._compute_subtotal(items) == 35.0

    def test_zero_amount_treated_as_falsy_falls_to_unit_price(self):
        items = [{"amount": 0, "unit_price": 10.0, "quantity": 2}]
        assert TaxService._compute_subtotal(items) == 20.0

    def test_mixed_amount_and_unit_price(self):
        items = [
            {"amount": 100.0},
            {"unit_price": 20.0, "quantity": 3},
        ]
        assert TaxService._compute_subtotal(items) == 160.0


@pytest.mark.unit
class TestBuildTaxLines:
    """Test TaxService._build_tax_lines static helper"""

    def test_builds_from_provider_response(self):
        lines = [
            {
                "line_item_id": "li_1",
                "sku_id": "sku_1",
                "tax_amount": 8.75,
                "rate": 0.0875,
                "jurisdiction": "CA",
                "tax_type": "sales",
            }
        ]
        result = TaxService._build_tax_lines(lines)
        assert len(result) == 1
        assert result[0].line_item_id == "li_1"
        assert result[0].tax_amount == 8.75
        assert result[0].tax_rate == 0.0875
        assert result[0].jurisdiction == "CA"

    def test_generates_line_item_id_if_missing(self):
        lines = [{"tax_amount": 5.0}]
        result = TaxService._build_tax_lines(lines)
        assert result[0].line_item_id == "line_0"

    def test_auto_increments_generated_ids(self):
        lines = [{}, {}, {}]
        result = TaxService._build_tax_lines(lines)
        assert result[0].line_item_id == "line_0"
        assert result[1].line_item_id == "line_1"
        assert result[2].line_item_id == "line_2"

    def test_defaults_tax_amount_to_zero(self):
        lines = [{"line_item_id": "li_1"}]
        result = TaxService._build_tax_lines(lines)
        assert result[0].tax_amount == 0.0

    def test_defaults_rate_to_zero(self):
        lines = [{"line_item_id": "li_1"}]
        result = TaxService._build_tax_lines(lines)
        assert result[0].tax_rate == 0.0

    def test_empty_lines_returns_empty(self):
        assert TaxService._build_tax_lines([]) == []

    def test_optional_fields_default_none(self):
        lines = [{"line_item_id": "li_1", "tax_amount": 1.0, "rate": 0.01}]
        result = TaxService._build_tax_lines(lines)
        assert result[0].jurisdiction is None
        assert result[0].tax_type is None
        assert result[0].sku_id is None

    def test_returns_tax_line_item_instances(self):
        lines = [{"tax_amount": 1.0}]
        result = TaxService._build_tax_lines(lines)
        assert isinstance(result[0], TaxLineItem)

    def test_multiple_lines(self):
        lines = [
            {"line_item_id": "a", "tax_amount": 5.0, "rate": 0.05},
            {"line_item_id": "b", "tax_amount": 10.0, "rate": 0.10},
        ]
        result = TaxService._build_tax_lines(lines)
        assert len(result) == 2
        assert result[0].tax_amount == 5.0
        assert result[1].tax_amount == 10.0


@pytest.mark.unit
class TestTaxLineItemModel:
    """Test TaxLineItem event model"""

    def test_creation(self):
        item = TaxLineItem(
            line_item_id="li_1", tax_amount=5.0, tax_rate=0.05
        )
        assert item.line_item_id == "li_1"

    def test_optional_fields(self):
        item = TaxLineItem(line_item_id="li_1", tax_amount=0.0, tax_rate=0.0)
        assert item.sku_id is None
        assert item.jurisdiction is None
        assert item.tax_type is None
