"""
Weather Service Contracts Package

Contract-Driven Development (CDD) test contracts for weather service.
"""

from .data_contract import (
    # Request Contracts
    WeatherCurrentRequestContract,
    WeatherForecastRequestContract,
    WeatherAlertQueryContract,
    LocationSaveRequestContract,
    LocationDeleteRequestContract,
    LocationListRequestContract,
    # Response Contracts
    WeatherCurrentResponseContract,
    WeatherForecastResponseContract,
    ForecastDayContract,
    WeatherAlertResponseContract,
    WeatherAlertContract,
    LocationResponseContract,
    LocationListResponseContract,
    ErrorResponseContract,
    # Factory
    WeatherTestDataFactory,
    # Builders
    WeatherCurrentRequestBuilder,
    WeatherForecastRequestBuilder,
    LocationSaveRequestBuilder,
)

__all__ = [
    # Request Contracts
    "WeatherCurrentRequestContract",
    "WeatherForecastRequestContract",
    "WeatherAlertQueryContract",
    "LocationSaveRequestContract",
    "LocationDeleteRequestContract",
    "LocationListRequestContract",
    # Response Contracts
    "WeatherCurrentResponseContract",
    "WeatherForecastResponseContract",
    "ForecastDayContract",
    "WeatherAlertResponseContract",
    "WeatherAlertContract",
    "LocationResponseContract",
    "LocationListResponseContract",
    "ErrorResponseContract",
    # Factory
    "WeatherTestDataFactory",
    # Builders
    "WeatherCurrentRequestBuilder",
    "WeatherForecastRequestBuilder",
    "LocationSaveRequestBuilder",
]
