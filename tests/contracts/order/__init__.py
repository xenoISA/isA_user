"""
Order Service Contracts

Data and logic contracts for order_service testing.
"""

from .data_contract import (
    # Request Contracts
    OrderCreateRequestContract,
    OrderUpdateRequestContract,
    OrderCancelRequestContract,
    OrderCompleteRequestContract,
    OrderListParamsContract,
    OrderSearchParamsContract,
    OrderFilterContract,
    # Response Contracts
    OrderResponseContract,
    OrderListResponseContract,
    OrderStatisticsResponseContract,
    OrderSummaryContract,
    # Test Data Factory
    OrderTestDataFactory,
    # Builders
    OrderCreateRequestBuilder,
    OrderUpdateRequestBuilder,
    OrderCancelRequestBuilder,
    OrderCompleteRequestBuilder,
)

__all__ = [
    # Request Contracts
    "OrderCreateRequestContract",
    "OrderUpdateRequestContract",
    "OrderCancelRequestContract",
    "OrderCompleteRequestContract",
    "OrderListParamsContract",
    "OrderSearchParamsContract",
    "OrderFilterContract",
    # Response Contracts
    "OrderResponseContract",
    "OrderListResponseContract",
    "OrderStatisticsResponseContract",
    "OrderSummaryContract",
    # Test Data Factory
    "OrderTestDataFactory",
    # Builders
    "OrderCreateRequestBuilder",
    "OrderUpdateRequestBuilder",
    "OrderCancelRequestBuilder",
    "OrderCompleteRequestBuilder",
]
