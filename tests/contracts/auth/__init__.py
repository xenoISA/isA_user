"""
Authentication Service Test Contracts

Import all contracts for easy access.
"""

from .data_contract import (
    # Request Contracts
    TokenVerificationRequestContract,
    DevTokenRequestContract,
    TokenPairRequestContract,
    RefreshTokenRequestContract,
    RegistrationStartRequestContract,
    RegistrationVerifyRequestContract,
    ApiKeyCreateRequestContract,
    ApiKeyVerifyRequestContract,
    DeviceRegisterRequestContract,
    DeviceAuthenticateRequestContract,
    DevicePairingGenerateRequestContract,
    DevicePairingVerifyRequestContract,

    # Response Contracts
    TokenVerificationResponseContract,
    TokenResponseContract,
    RegistrationStartResponseContract,
    RegistrationVerifyResponseContract,
    ApiKeyCreateResponseContract,
    ApiKeyVerifyResponseContract,
    DeviceRegisterResponseContract,
    DeviceAuthenticateResponseContract,
    DevicePairingResponseContract,
    UserInfoResponseContract,

    # Factory
    AuthTestDataFactory,

    # Builders
    TokenPairRequestBuilder,
    DeviceRegisterRequestBuilder,
    ApiKeyCreateRequestBuilder,
)

__all__ = [
    # Request Contracts
    "TokenVerificationRequestContract",
    "DevTokenRequestContract",
    "TokenPairRequestContract",
    "RefreshTokenRequestContract",
    "RegistrationStartRequestContract",
    "RegistrationVerifyRequestContract",
    "ApiKeyCreateRequestContract",
    "ApiKeyVerifyRequestContract",
    "DeviceRegisterRequestContract",
    "DeviceAuthenticateRequestContract",
    "DevicePairingGenerateRequestContract",
    "DevicePairingVerifyRequestContract",

    # Response Contracts
    "TokenVerificationResponseContract",
    "TokenResponseContract",
    "RegistrationStartResponseContract",
    "RegistrationVerifyResponseContract",
    "ApiKeyCreateResponseContract",
    "ApiKeyVerifyResponseContract",
    "DeviceRegisterResponseContract",
    "DeviceAuthenticateResponseContract",
    "DevicePairingResponseContract",
    "UserInfoResponseContract",

    # Factory
    "AuthTestDataFactory",

    # Builders
    "TokenPairRequestBuilder",
    "DeviceRegisterRequestBuilder",
    "ApiKeyCreateRequestBuilder",
]
