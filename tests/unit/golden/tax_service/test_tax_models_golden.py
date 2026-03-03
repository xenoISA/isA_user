"""
Tax Models Golden Tests

GOLDEN: These tests document CURRENT behavior of tax models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden/tax_service -v
"""
import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from microservices.tax_service.models import (
    TaxLine,
    TaxCalculation,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# TaxLine Model Tests
# =============================================================================

class TestTaxLineModel:
    """Characterization: TaxLine model current behavior"""

    def test_create_minimal_tax_line(self):
        """CHAR: TaxLine can be created with required fields"""
        line = TaxLine(
            line_item_id="item_001",
            tax_amount=Decimal("5.99"),
        )
        assert line.line_item_id == "item_001"
        assert line.tax_amount == Decimal("5.99")
        assert line.jurisdiction is None
        assert line.rate is None

    def test_create_full_tax_line(self):
        """CHAR: TaxLine can be created with all fields"""
        line = TaxLine(
            line_item_id="item_002",
            tax_amount=Decimal("12.50"),
            jurisdiction="CA",
            rate=Decimal("0.0725"),
        )
        assert line.jurisdiction == "CA"
        assert line.rate == Decimal("0.0725")

    def test_tax_amount_cannot_be_negative(self):
        """CHAR: tax_amount must be >= 0"""
        with pytest.raises(ValidationError):
            TaxLine(line_item_id="item_001", tax_amount=Decimal("-1.00"))

    def test_tax_amount_can_be_zero(self):
        """CHAR: tax_amount can be zero (tax-exempt items)"""
        line = TaxLine(line_item_id="item_001", tax_amount=Decimal("0"))
        assert line.tax_amount == Decimal("0")

    def test_line_item_id_required(self):
        """CHAR: line_item_id is required"""
        with pytest.raises(ValidationError):
            TaxLine(tax_amount=Decimal("5.00"))

    def test_tax_amount_required(self):
        """CHAR: tax_amount is required"""
        with pytest.raises(ValidationError):
            TaxLine(line_item_id="item_001")

    def test_tax_amount_precision(self):
        """CHAR: Decimal precision is preserved"""
        line = TaxLine(
            line_item_id="item_001",
            tax_amount=Decimal("0.01"),
        )
        assert line.tax_amount == Decimal("0.01")


# =============================================================================
# TaxCalculation Model Tests
# =============================================================================

class TestTaxCalculationModel:
    """Characterization: TaxCalculation model current behavior"""

    def test_create_minimal_calculation(self):
        """CHAR: TaxCalculation can be created with required fields"""
        calc = TaxCalculation(
            calculation_id="calc_001",
            order_id="order_001",
        )
        assert calc.calculation_id == "calc_001"
        assert calc.order_id == "order_001"
        assert calc.currency == "USD"
        assert calc.total_tax == Decimal("0")
        assert calc.lines == []
        assert calc.created_at is None
        assert calc.metadata == {}

    def test_create_full_calculation(self):
        """CHAR: TaxCalculation can be created with all fields"""
        now = datetime.utcnow()
        lines = [
            TaxLine(line_item_id="i1", tax_amount=Decimal("5.00"), jurisdiction="CA"),
            TaxLine(line_item_id="i2", tax_amount=Decimal("3.00"), jurisdiction="CA"),
        ]
        calc = TaxCalculation(
            calculation_id="calc_002",
            order_id="order_002",
            currency="EUR",
            total_tax=Decimal("8.00"),
            lines=lines,
            created_at=now,
            metadata={"method": "mock"},
        )
        assert calc.currency == "EUR"
        assert calc.total_tax == Decimal("8.00")
        assert len(calc.lines) == 2
        assert calc.metadata == {"method": "mock"}

    def test_default_currency_is_usd(self):
        """CHAR: Default currency is USD"""
        calc = TaxCalculation(calculation_id="c1", order_id="o1")
        assert calc.currency == "USD"

    def test_default_total_tax_is_zero(self):
        """CHAR: Default total_tax is 0"""
        calc = TaxCalculation(calculation_id="c1", order_id="o1")
        assert calc.total_tax == Decimal("0")

    def test_default_lines_empty_list(self):
        """CHAR: Default lines is empty list"""
        calc = TaxCalculation(calculation_id="c1", order_id="o1")
        assert calc.lines == []
        assert isinstance(calc.lines, list)

    def test_default_metadata_empty_dict(self):
        """CHAR: Default metadata is empty dict"""
        calc = TaxCalculation(calculation_id="c1", order_id="o1")
        assert calc.metadata == {}
        assert isinstance(calc.metadata, dict)

    def test_total_tax_cannot_be_negative(self):
        """CHAR: total_tax must be >= 0"""
        with pytest.raises(ValidationError):
            TaxCalculation(
                calculation_id="c1", order_id="o1",
                total_tax=Decimal("-1.00"),
            )

    def test_total_tax_can_be_zero(self):
        """CHAR: total_tax can be zero"""
        calc = TaxCalculation(
            calculation_id="c1", order_id="o1",
            total_tax=Decimal("0"),
        )
        assert calc.total_tax == Decimal("0")

    def test_calculation_id_required(self):
        """CHAR: calculation_id is required"""
        with pytest.raises(ValidationError):
            TaxCalculation(order_id="o1")

    def test_order_id_required(self):
        """CHAR: order_id is required"""
        with pytest.raises(ValidationError):
            TaxCalculation(calculation_id="c1")

    def test_multiple_tax_lines(self):
        """CHAR: Calculation supports multiple tax lines"""
        lines = [
            TaxLine(line_item_id=f"item_{i}", tax_amount=Decimal("1.00"))
            for i in range(5)
        ]
        calc = TaxCalculation(
            calculation_id="c1", order_id="o1", lines=lines,
        )
        assert len(calc.lines) == 5

    def test_total_tax_precision(self):
        """CHAR: Decimal precision is preserved for total_tax"""
        calc = TaxCalculation(
            calculation_id="c1", order_id="o1",
            total_tax=Decimal("123.456"),
        )
        assert calc.total_tax == Decimal("123.456")
