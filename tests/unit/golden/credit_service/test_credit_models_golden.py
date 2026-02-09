"""
Credit Models Golden Tests

🔒 GOLDEN: These tests document CURRENT behavior of credit models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden/credit_service -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.credit_service.models import (
    CreditTypeEnum,
    TransactionTypeEnum,
    AllocationStatusEnum,
    ExpirationPolicyEnum,
    ReferenceTypeEnum,
    CreditAccount,
    CreditTransaction,
    CreditAllocation,
    CreditCampaign,
    CreateAccountRequest,
    AllocateCreditsRequest,
    ConsumeCreditsRequest,
    CheckAvailabilityRequest,
    TransferCreditsRequest,
    CreateCampaignRequest,
    TransactionQueryRequest,
    BalanceQueryRequest,
    AccountQueryRequest,
    CreditAccountResponse,
    CreditAccountListResponse,
    NextExpiration,
    CreditBalanceSummary,
    AllocationResponse,
    ConsumptionTransaction,
    ConsumptionResponse,
    ConsumptionPlanItem,
    AvailabilityResponse,
    TransferResponse,
    CreditTransactionResponse,
    TransactionListResponse,
    CreditCampaignResponse,
    CreditTypeBreakdown,
    CreditStatisticsResponse,
    HealthCheckResponse,
    DetailedHealthCheckResponse,
    ErrorResponse,
    SuccessResponse,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# Enum Tests - Current Behavior
# =============================================================================

class TestCreditTypeEnum:
    """Characterization: CreditTypeEnum current behavior"""

    def test_all_credit_types_defined(self):
        """CHAR: All expected credit types are defined"""
        expected_types = {
            "promotional", "bonus", "referral", "subscription", "compensation"
        }
        actual_types = {ct.value for ct in CreditTypeEnum}
        assert actual_types == expected_types

    def test_credit_type_values(self):
        """CHAR: Credit type values are correct"""
        assert CreditTypeEnum.PROMOTIONAL.value == "promotional"
        assert CreditTypeEnum.BONUS.value == "bonus"
        assert CreditTypeEnum.REFERRAL.value == "referral"
        assert CreditTypeEnum.SUBSCRIPTION.value == "subscription"
        assert CreditTypeEnum.COMPENSATION.value == "compensation"


class TestTransactionTypeEnum:
    """Characterization: TransactionTypeEnum current behavior"""

    def test_all_transaction_types_defined(self):
        """CHAR: All expected transaction types are defined"""
        expected_types = {
            "allocate", "consume", "expire", "transfer_in", "transfer_out", "adjust"
        }
        actual_types = {tt.value for tt in TransactionTypeEnum}
        assert actual_types == expected_types

    def test_transaction_type_values(self):
        """CHAR: Transaction type values are correct"""
        assert TransactionTypeEnum.ALLOCATE.value == "allocate"
        assert TransactionTypeEnum.CONSUME.value == "consume"
        assert TransactionTypeEnum.EXPIRE.value == "expire"
        assert TransactionTypeEnum.TRANSFER_IN.value == "transfer_in"
        assert TransactionTypeEnum.TRANSFER_OUT.value == "transfer_out"
        assert TransactionTypeEnum.ADJUST.value == "adjust"


class TestAllocationStatusEnum:
    """Characterization: AllocationStatusEnum current behavior"""

    def test_all_allocation_statuses_defined(self):
        """CHAR: All expected allocation statuses are defined"""
        expected_statuses = {
            "pending", "completed", "failed", "revoked", "expired"
        }
        actual_statuses = {a_s.value for a_s in AllocationStatusEnum}
        assert actual_statuses == expected_statuses

    def test_allocation_status_values(self):
        """CHAR: Allocation status values are correct"""
        assert AllocationStatusEnum.PENDING.value == "pending"
        assert AllocationStatusEnum.COMPLETED.value == "completed"
        assert AllocationStatusEnum.FAILED.value == "failed"
        assert AllocationStatusEnum.REVOKED.value == "revoked"
        assert AllocationStatusEnum.EXPIRED.value == "expired"


class TestExpirationPolicyEnum:
    """Characterization: ExpirationPolicyEnum current behavior"""

    def test_all_expiration_policies_defined(self):
        """CHAR: All expected expiration policies are defined"""
        expected_policies = {
            "fixed_days", "end_of_month", "end_of_year", "subscription_period", "never"
        }
        actual_policies = {ep.value for ep in ExpirationPolicyEnum}
        assert actual_policies == expected_policies

    def test_expiration_policy_values(self):
        """CHAR: Expiration policy values are correct"""
        assert ExpirationPolicyEnum.FIXED_DAYS.value == "fixed_days"
        assert ExpirationPolicyEnum.END_OF_MONTH.value == "end_of_month"
        assert ExpirationPolicyEnum.END_OF_YEAR.value == "end_of_year"
        assert ExpirationPolicyEnum.SUBSCRIPTION_PERIOD.value == "subscription_period"
        assert ExpirationPolicyEnum.NEVER.value == "never"


class TestReferenceTypeEnum:
    """Characterization: ReferenceTypeEnum current behavior"""

    def test_all_reference_types_defined(self):
        """CHAR: All expected reference types are defined"""
        expected_types = {
            "campaign", "billing", "refund", "subscription", "manual", "transfer"
        }
        actual_types = {rt.value for rt in ReferenceTypeEnum}
        assert actual_types == expected_types

    def test_reference_type_values(self):
        """CHAR: Reference type values are correct"""
        assert ReferenceTypeEnum.CAMPAIGN.value == "campaign"
        assert ReferenceTypeEnum.BILLING.value == "billing"
        assert ReferenceTypeEnum.REFUND.value == "refund"
        assert ReferenceTypeEnum.SUBSCRIPTION.value == "subscription"
        assert ReferenceTypeEnum.MANUAL.value == "manual"
        assert ReferenceTypeEnum.TRANSFER.value == "transfer"


# =============================================================================
# CreditAccount - Current Behavior
# =============================================================================

class TestCreditAccountChar:
    """Characterization: CreditAccount current behavior"""

    def test_accepts_minimal_credit_account(self):
        """CHAR: Minimal credit account is accepted"""
        account = CreditAccount(
            account_id="cred_acc_123",
            user_id="user_123",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
            expiration_days=90
        )
        assert account.account_id == "cred_acc_123"
        assert account.user_id == "user_123"
        assert account.credit_type == CreditTypeEnum.PROMOTIONAL
        assert account.balance == 0  # Default
        assert account.total_allocated == 0  # Default
        assert account.total_consumed == 0  # Default
        assert account.total_expired == 0  # Default
        assert account.currency == "CREDIT"  # Default
        assert account.is_active is True  # Default
        assert account.metadata == {}  # Default

    def test_accepts_full_credit_account(self):
        """CHAR: Full credit account with all fields is accepted"""
        now = datetime.now(timezone.utc)
        account = CreditAccount(
            id=1,
            account_id="cred_acc_full_123",
            user_id="user_123",
            organization_id="org_123",
            credit_type=CreditTypeEnum.BONUS,
            balance=5000,
            total_allocated=10000,
            total_consumed=3000,
            total_expired=2000,
            currency="CREDIT",
            expiration_policy=ExpirationPolicyEnum.END_OF_MONTH,
            expiration_days=30,
            is_active=True,
            metadata={"source": "campaign_123"},
            created_at=now,
            updated_at=now
        )
        assert account.organization_id == "org_123"
        assert account.balance == 5000
        assert account.total_allocated == 10000
        assert account.metadata["source"] == "campaign_123"

    def test_user_id_cannot_be_empty(self):
        """CHAR: user_id cannot be empty string"""
        with pytest.raises(ValidationError, match="string_too_short"):
            CreditAccount(
                account_id="cred_acc_123",
                user_id="",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
                expiration_days=90
            )

    def test_user_id_whitespace_trimmed(self):
        """CHAR: user_id whitespace is trimmed"""
        account = CreditAccount(
            account_id="cred_acc_123",
            user_id="  user_123  ",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
            expiration_days=90
        )
        assert account.user_id == "user_123"

    def test_balance_must_be_non_negative(self):
        """CHAR: balance must be >= 0"""
        with pytest.raises(ValidationError):
            CreditAccount(
                account_id="cred_acc_123",
                user_id="user_123",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                balance=-100,
                expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
                expiration_days=90
            )

    def test_expiration_days_range(self):
        """CHAR: expiration_days must be between 1 and 365"""
        # Valid minimum
        account_min = CreditAccount(
            account_id="cred_acc_123",
            user_id="user_123",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
            expiration_days=1
        )
        assert account_min.expiration_days == 1

        # Valid maximum
        account_max = CreditAccount(
            account_id="cred_acc_456",
            user_id="user_123",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
            expiration_days=365
        )
        assert account_max.expiration_days == 365

        # Invalid: zero
        with pytest.raises(ValidationError):
            CreditAccount(
                account_id="cred_acc_789",
                user_id="user_123",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
                expiration_days=0
            )

        # Invalid: too large
        with pytest.raises(ValidationError):
            CreditAccount(
                account_id="cred_acc_999",
                user_id="user_123",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
                expiration_days=366
            )


# =============================================================================
# CreditTransaction - Current Behavior
# =============================================================================

class TestCreditTransactionChar:
    """Characterization: CreditTransaction current behavior"""

    def test_accepts_minimal_transaction(self):
        """CHAR: Minimal transaction is accepted"""
        transaction = CreditTransaction(
            transaction_id="cred_txn_123",
            account_id="cred_acc_123",
            user_id="user_123",
            transaction_type=TransactionTypeEnum.ALLOCATE,
            amount=1000,
            balance_before=0,
            balance_after=1000
        )
        assert transaction.transaction_id == "cred_txn_123"
        assert transaction.account_id == "cred_acc_123"
        assert transaction.amount == 1000
        assert transaction.metadata == {}  # Default

    def test_accepts_full_transaction(self):
        """CHAR: Full transaction with all fields is accepted"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=90)

        transaction = CreditTransaction(
            id=1,
            transaction_id="cred_txn_full_123",
            account_id="cred_acc_123",
            user_id="user_123",
            transaction_type=TransactionTypeEnum.CONSUME,
            amount=-500,
            balance_before=1000,
            balance_after=500,
            reference_id="bill_123",
            reference_type=ReferenceTypeEnum.BILLING,
            description="Usage billing consumption",
            metadata={"session_id": "sess_123"},
            expires_at=expires,
            created_at=now
        )
        assert transaction.reference_id == "bill_123"
        assert transaction.reference_type == ReferenceTypeEnum.BILLING
        assert transaction.description == "Usage billing consumption"

    def test_amount_can_be_negative(self):
        """CHAR: amount can be negative (for consume, expire operations)"""
        transaction = CreditTransaction(
            transaction_id="cred_txn_consume_123",
            account_id="cred_acc_123",
            user_id="user_123",
            transaction_type=TransactionTypeEnum.CONSUME,
            amount=-500,
            balance_before=1000,
            balance_after=500
        )
        assert transaction.amount == -500

    def test_balance_fields_non_negative(self):
        """CHAR: balance_before and balance_after must be >= 0"""
        with pytest.raises(ValidationError):
            CreditTransaction(
                transaction_id="cred_txn_123",
                account_id="cred_acc_123",
                user_id="user_123",
                transaction_type=TransactionTypeEnum.CONSUME,
                amount=-500,
                balance_before=-100,
                balance_after=0
            )


# =============================================================================
# CreditAllocation - Current Behavior
# =============================================================================

class TestCreditAllocationChar:
    """Characterization: CreditAllocation current behavior"""

    def test_accepts_allocation(self):
        """CHAR: Valid allocation is accepted"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=90)

        allocation = CreditAllocation(
            allocation_id="cred_alloc_123",
            account_id="cred_acc_123",
            user_id="user_123",
            amount=1000,
            remaining_balance=1000,
            status=AllocationStatusEnum.COMPLETED,
            expires_at=expires
        )
        assert allocation.allocation_id == "cred_alloc_123"
        assert allocation.amount == 1000
        assert allocation.remaining_balance == 1000
        assert allocation.status == AllocationStatusEnum.COMPLETED

    def test_allocation_with_campaign(self):
        """CHAR: Allocation with campaign reference"""
        allocation = CreditAllocation(
            allocation_id="cred_alloc_123",
            account_id="cred_acc_123",
            user_id="user_123",
            campaign_id="camp_123",
            amount=500,
            remaining_balance=500,
            status=AllocationStatusEnum.COMPLETED
        )
        assert allocation.campaign_id == "camp_123"

    def test_amount_must_be_positive(self):
        """CHAR: amount must be > 0"""
        with pytest.raises(ValidationError):
            CreditAllocation(
                allocation_id="cred_alloc_123",
                account_id="cred_acc_123",
                user_id="user_123",
                amount=0,
                remaining_balance=0,
                status=AllocationStatusEnum.COMPLETED
            )

    def test_remaining_balance_non_negative(self):
        """CHAR: remaining_balance must be >= 0"""
        with pytest.raises(ValidationError):
            CreditAllocation(
                allocation_id="cred_alloc_123",
                account_id="cred_acc_123",
                user_id="user_123",
                amount=1000,
                remaining_balance=-100,
                status=AllocationStatusEnum.COMPLETED
            )


# =============================================================================
# CreditCampaign - Current Behavior
# =============================================================================

class TestCreditCampaignChar:
    """Characterization: CreditCampaign current behavior"""

    def test_accepts_minimal_campaign(self):
        """CHAR: Minimal campaign is accepted"""
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=30)

        campaign = CreditCampaign(
            campaign_id="camp_123",
            name="Holiday Promotion",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            credit_amount=1000,
            total_budget=100000,
            remaining_budget=100000,
            start_date=now,
            end_date=end_date,
            expiration_days=90
        )
        assert campaign.campaign_id == "camp_123"
        assert campaign.name == "Holiday Promotion"
        assert campaign.allocated_amount == 0  # Default
        assert campaign.allocation_count == 0  # Default
        assert campaign.is_active is True  # Default

    def test_accepts_full_campaign(self):
        """CHAR: Full campaign with all fields is accepted"""
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=30)

        campaign = CreditCampaign(
            id=1,
            campaign_id="camp_full_123",
            name="Summer Special",
            description="Summer promotional campaign",
            credit_type=CreditTypeEnum.BONUS,
            credit_amount=500,
            total_budget=500000,
            allocated_amount=100000,
            remaining_budget=400000,
            allocation_count=200,
            eligibility_rules={"min_account_age_days": 30},
            allocation_rules={"trigger": "signup"},
            start_date=now,
            end_date=end_date,
            expiration_days=60,
            max_allocations_per_user=1,
            is_active=True,
            metadata={"category": "seasonal"},
            created_at=now,
            updated_at=now
        )
        assert campaign.description == "Summer promotional campaign"
        assert campaign.eligibility_rules["min_account_age_days"] == 30

    def test_campaign_name_cannot_be_empty(self):
        """CHAR: name cannot be empty string"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="string_too_short"):
            CreditCampaign(
                campaign_id="camp_123",
                name="",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                credit_amount=1000,
                total_budget=100000,
                remaining_budget=100000,
                start_date=now,
                end_date=now + timedelta(days=30),
                expiration_days=90
            )

    def test_campaign_name_whitespace_trimmed(self):
        """CHAR: name whitespace is trimmed"""
        now = datetime.now(timezone.utc)
        campaign = CreditCampaign(
            campaign_id="camp_123",
            name="  Holiday Promo  ",
            credit_type=CreditTypeEnum.PROMOTIONAL,
            credit_amount=1000,
            total_budget=100000,
            remaining_budget=100000,
            start_date=now,
            end_date=now + timedelta(days=30),
            expiration_days=90
        )
        assert campaign.name == "Holiday Promo"

    def test_credit_amount_must_be_positive(self):
        """CHAR: credit_amount must be > 0"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            CreditCampaign(
                campaign_id="camp_123",
                name="Campaign",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                credit_amount=0,
                total_budget=100000,
                remaining_budget=100000,
                start_date=now,
                end_date=now + timedelta(days=30),
                expiration_days=90
            )

    def test_total_budget_must_be_positive(self):
        """CHAR: total_budget must be > 0"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            CreditCampaign(
                campaign_id="camp_123",
                name="Campaign",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                credit_amount=1000,
                total_budget=-1,
                remaining_budget=0,
                start_date=now,
                end_date=now + timedelta(days=30),
                expiration_days=90
            )


# =============================================================================
# CreateAccountRequest - Current Behavior
# =============================================================================

class TestCreateAccountRequestChar:
    """Characterization: CreateAccountRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal create account request is accepted"""
        request = CreateAccountRequest(
            user_id="user_123",
            credit_type="promotional"
        )
        assert request.user_id == "user_123"
        assert request.credit_type == "promotional"
        assert request.expiration_policy == "fixed_days"  # Default
        assert request.expiration_days == 90  # Default
        assert request.metadata == {}  # Default

    def test_accepts_full_request(self):
        """CHAR: Full create account request is accepted"""
        request = CreateAccountRequest(
            user_id="user_123",
            organization_id="org_123",
            credit_type="bonus",
            expiration_policy="end_of_month",
            expiration_days=30,
            metadata={"source": "referral"}
        )
        assert request.organization_id == "org_123"
        assert request.expiration_policy == "end_of_month"
        assert request.metadata["source"] == "referral"

    def test_user_id_validation(self):
        """CHAR: user_id validation rules"""
        # Empty user_id rejected
        with pytest.raises(ValidationError, match="string_too_short"):
            CreateAccountRequest(
                user_id="",
                credit_type="promotional"
            )

        # Whitespace-only rejected by custom validator
        with pytest.raises(ValidationError, match="user_id cannot be empty"):
            CreateAccountRequest(
                user_id="   ",
                credit_type="promotional"
            )

    def test_credit_type_validation(self):
        """CHAR: credit_type must be valid enum value"""
        with pytest.raises(ValidationError, match="credit_type must be one of"):
            CreateAccountRequest(
                user_id="user_123",
                credit_type="invalid_type"
            )

    def test_expiration_policy_validation(self):
        """CHAR: expiration_policy must be valid enum value"""
        with pytest.raises(ValidationError, match="expiration_policy must be one of"):
            CreateAccountRequest(
                user_id="user_123",
                credit_type="promotional",
                expiration_policy="invalid_policy"
            )


# =============================================================================
# AllocateCreditsRequest - Current Behavior
# =============================================================================

class TestAllocateCreditsRequestChar:
    """Characterization: AllocateCreditsRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal allocate request is accepted"""
        request = AllocateCreditsRequest(
            user_id="user_123",
            credit_type="bonus",
            amount=1000
        )
        assert request.user_id == "user_123"
        assert request.credit_type == "bonus"
        assert request.amount == 1000
        assert request.campaign_id is None
        assert request.metadata == {}

    def test_accepts_full_request(self):
        """CHAR: Full allocate request is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=90)
        request = AllocateCreditsRequest(
            user_id="user_123",
            credit_type="promotional",
            amount=5000,
            campaign_id="camp_123",
            description="Sign-up bonus",
            expires_at=expires,
            metadata={"source": "campaign"}
        )
        assert request.campaign_id == "camp_123"
        assert request.description == "Sign-up bonus"

    def test_amount_must_be_positive(self):
        """CHAR: amount must be > 0"""
        with pytest.raises(ValidationError):
            AllocateCreditsRequest(
                user_id="user_123",
                credit_type="bonus",
                amount=0
            )

        with pytest.raises(ValidationError):
            AllocateCreditsRequest(
                user_id="user_123",
                credit_type="bonus",
                amount=-100
            )


# =============================================================================
# ConsumeCreditsRequest - Current Behavior
# =============================================================================

class TestConsumeCreditsRequestChar:
    """Characterization: ConsumeCreditsRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal consume request is accepted"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            amount=500
        )
        assert request.user_id == "user_123"
        assert request.amount == 500
        assert request.billing_record_id is None
        assert request.metadata == {}

    def test_accepts_full_request(self):
        """CHAR: Full consume request is accepted"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            amount=1000,
            billing_record_id="bill_123",
            description="Usage billing",
            metadata={"session_id": "sess_123"}
        )
        assert request.billing_record_id == "bill_123"
        assert request.description == "Usage billing"

    def test_amount_must_be_positive(self):
        """CHAR: amount must be > 0"""
        with pytest.raises(ValidationError):
            ConsumeCreditsRequest(
                user_id="user_123",
                amount=0
            )


# =============================================================================
# CheckAvailabilityRequest - Current Behavior
# =============================================================================

class TestCheckAvailabilityRequestChar:
    """Characterization: CheckAvailabilityRequest current behavior"""

    def test_accepts_request(self):
        """CHAR: Valid availability check request is accepted"""
        request = CheckAvailabilityRequest(
            user_id="user_123",
            amount=2000
        )
        assert request.user_id == "user_123"
        assert request.amount == 2000

    def test_amount_must_be_positive(self):
        """CHAR: amount must be > 0"""
        with pytest.raises(ValidationError):
            CheckAvailabilityRequest(
                user_id="user_123",
                amount=-100
            )


# =============================================================================
# TransferCreditsRequest - Current Behavior
# =============================================================================

class TestTransferCreditsRequestChar:
    """Characterization: TransferCreditsRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal transfer request is accepted"""
        request = TransferCreditsRequest(
            from_user_id="user_123",
            to_user_id="user_456",
            credit_type="bonus",
            amount=500
        )
        assert request.from_user_id == "user_123"
        assert request.to_user_id == "user_456"
        assert request.amount == 500
        assert request.metadata == {}

    def test_accepts_full_request(self):
        """CHAR: Full transfer request is accepted"""
        request = TransferCreditsRequest(
            from_user_id="user_123",
            to_user_id="user_456",
            credit_type="bonus",
            amount=1000,
            description="Gift transfer",
            metadata={"reason": "gift"}
        )
        assert request.description == "Gift transfer"

    def test_user_ids_validation(self):
        """CHAR: user_ids cannot be empty"""
        with pytest.raises(ValidationError):
            TransferCreditsRequest(
                from_user_id="",
                to_user_id="user_456",
                credit_type="bonus",
                amount=500
            )


# =============================================================================
# CreateCampaignRequest - Current Behavior
# =============================================================================

class TestCreateCampaignRequestChar:
    """Characterization: CreateCampaignRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal campaign request is accepted"""
        now = datetime.now(timezone.utc)
        request = CreateCampaignRequest(
            name="Holiday Campaign",
            credit_type="promotional",
            credit_amount=1000,
            total_budget=100000,
            start_date=now,
            end_date=now + timedelta(days=30)
        )
        assert request.name == "Holiday Campaign"
        assert request.expiration_days == 90  # Default
        assert request.max_allocations_per_user == 1  # Default

    def test_accepts_full_request(self):
        """CHAR: Full campaign request is accepted"""
        now = datetime.now(timezone.utc)
        request = CreateCampaignRequest(
            name="Summer Promo",
            description="Summer promotional campaign",
            credit_type="bonus",
            credit_amount=500,
            total_budget=500000,
            eligibility_rules={"min_account_age_days": 30},
            allocation_rules={"trigger": "signup"},
            start_date=now,
            end_date=now + timedelta(days=60),
            expiration_days=60,
            max_allocations_per_user=2,
            metadata={"category": "seasonal"}
        )
        assert request.description == "Summer promotional campaign"
        assert request.max_allocations_per_user == 2

    def test_name_validation(self):
        """CHAR: name cannot be empty"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match="string_too_short"):
            CreateCampaignRequest(
                name="",
                credit_type="promotional",
                credit_amount=1000,
                total_budget=100000,
                start_date=now,
                end_date=now + timedelta(days=30)
            )


# =============================================================================
# TransactionQueryRequest - Current Behavior
# =============================================================================

class TestTransactionQueryRequestChar:
    """Characterization: TransactionQueryRequest current behavior"""

    def test_accepts_minimal_request(self):
        """CHAR: Minimal query request is accepted"""
        request = TransactionQueryRequest(
            user_id="user_123"
        )
        assert request.user_id == "user_123"
        assert request.page == 1  # Default
        assert request.page_size == 50  # Default

    def test_accepts_full_request(self):
        """CHAR: Full query request is accepted"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)
        request = TransactionQueryRequest(
            user_id="user_123",
            account_id="cred_acc_123",
            transaction_type="consume",
            start_date=start,
            end_date=end,
            page=2,
            page_size=100
        )
        assert request.account_id == "cred_acc_123"
        assert request.page == 2
        assert request.page_size == 100

    def test_page_validation(self):
        """CHAR: page must be >= 1"""
        with pytest.raises(ValidationError):
            TransactionQueryRequest(
                user_id="user_123",
                page=0
            )

    def test_page_size_validation(self):
        """CHAR: page_size must be between 1 and 100"""
        with pytest.raises(ValidationError):
            TransactionQueryRequest(
                user_id="user_123",
                page_size=101
            )


# =============================================================================
# Response Models - Current Behavior
# =============================================================================

class TestCreditAccountResponseChar:
    """Characterization: CreditAccountResponse current behavior"""

    def test_accepts_account_response(self):
        """CHAR: Valid account response is accepted"""
        now = datetime.now(timezone.utc)
        response = CreditAccountResponse(
            account_id="cred_acc_123",
            user_id="user_123",
            credit_type="promotional",
            balance=5000,
            total_allocated=10000,
            total_consumed=3000,
            total_expired=2000,
            expiration_policy="fixed_days",
            expiration_days=90,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        assert response.account_id == "cred_acc_123"
        assert response.balance == 5000
        assert response.currency == "CREDIT"  # Default


class TestAllocationResponseChar:
    """Characterization: AllocationResponse current behavior"""

    def test_accepts_allocation_response(self):
        """CHAR: Valid allocation response is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=90)
        response = AllocationResponse(
            success=True,
            message="Credits allocated successfully",
            allocation_id="cred_alloc_123",
            account_id="cred_acc_123",
            amount=1000,
            balance_after=6000,
            expires_at=expires
        )
        assert response.success is True
        assert response.amount == 1000
        assert response.balance_after == 6000


class TestConsumptionResponseChar:
    """Characterization: ConsumptionResponse current behavior"""

    def test_accepts_consumption_response(self):
        """CHAR: Valid consumption response is accepted"""
        response = ConsumptionResponse(
            success=True,
            message="Credits consumed successfully",
            amount_consumed=500,
            balance_before=1000,
            balance_after=500,
            transactions=[
                ConsumptionTransaction(
                    transaction_id="cred_txn_123",
                    account_id="cred_acc_123",
                    amount=500,
                    credit_type="promotional"
                )
            ]
        )
        assert response.success is True
        assert response.amount_consumed == 500
        assert len(response.transactions) == 1


class TestAvailabilityResponseChar:
    """Characterization: AvailabilityResponse current behavior"""

    def test_accepts_availability_response(self):
        """CHAR: Valid availability response is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=90)
        response = AvailabilityResponse(
            available=True,
            total_balance=5000,
            requested_amount=2000,
            deficit=0,
            consumption_plan=[
                ConsumptionPlanItem(
                    account_id="cred_acc_123",
                    credit_type="promotional",
                    amount=2000,
                    expires_at=expires
                )
            ]
        )
        assert response.available is True
        assert response.total_balance == 5000
        assert len(response.consumption_plan) == 1


class TestTransferResponseChar:
    """Characterization: TransferResponse current behavior"""

    def test_accepts_transfer_response(self):
        """CHAR: Valid transfer response is accepted"""
        response = TransferResponse(
            success=True,
            message="Transfer successful",
            transfer_id="trf_123",
            from_transaction_id="cred_txn_123",
            to_transaction_id="cred_txn_456",
            amount=500,
            from_balance_after=500,
            to_balance_after=1500
        )
        assert response.success is True
        assert response.amount == 500
        assert response.transfer_id == "trf_123"


class TestCreditBalanceSummaryChar:
    """Characterization: CreditBalanceSummary current behavior"""

    def test_accepts_balance_summary(self):
        """CHAR: Valid balance summary is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        summary = CreditBalanceSummary(
            user_id="user_123",
            total_balance=10000,
            available_balance=10000,
            expiring_soon=2000,
            by_type={
                "promotional": 4000,
                "bonus": 3000,
                "referral": 2000,
                "subscription": 1000
            },
            next_expiration=NextExpiration(
                amount=2000,
                expires_at=expires
            )
        )
        assert summary.total_balance == 10000
        assert summary.by_type["promotional"] == 4000


class TestCreditCampaignResponseChar:
    """Characterization: CreditCampaignResponse current behavior"""

    def test_accepts_campaign_response(self):
        """CHAR: Valid campaign response is accepted"""
        now = datetime.now(timezone.utc)
        response = CreditCampaignResponse(
            campaign_id="camp_123",
            name="Holiday Promo",
            credit_type="promotional",
            credit_amount=1000,
            total_budget=100000,
            allocated_amount=50000,
            remaining_budget=50000,
            allocation_count=50,
            start_date=now,
            end_date=now + timedelta(days=30),
            expiration_days=90,
            max_allocations_per_user=1,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        assert response.campaign_id == "camp_123"
        assert response.remaining_budget == 50000


class TestCreditStatisticsResponseChar:
    """Characterization: CreditStatisticsResponse current behavior"""

    def test_accepts_statistics_response(self):
        """CHAR: Valid statistics response is accepted"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)

        stats = CreditStatisticsResponse(
            period_start=start,
            period_end=end,
            total_allocated=100000,
            total_consumed=60000,
            total_expired=10000,
            utilization_rate=0.6,
            expiration_rate=0.1,
            by_credit_type={
                "promotional": CreditTypeBreakdown(
                    allocated=40000,
                    consumed=25000,
                    expired=5000
                ),
                "bonus": CreditTypeBreakdown(
                    allocated=30000,
                    consumed=20000,
                    expired=3000
                )
            },
            active_campaigns=5,
            active_accounts=100
        )
        assert stats.total_allocated == 100000
        assert stats.utilization_rate == 0.6
        assert stats.active_campaigns == 5


# =============================================================================
# Health Response - Current Behavior
# =============================================================================

class TestHealthCheckResponseChar:
    """Characterization: HealthCheckResponse current behavior"""

    def test_accepts_health_response(self):
        """CHAR: Valid health response is accepted"""
        response = HealthCheckResponse(
            status="operational",
            service="credit_service",
            port=8229,
            version="1.0.0",
            timestamp="2025-12-18T10:00:00Z"
        )
        assert response.status == "operational"
        assert response.service == "credit_service"
        assert response.port == 8229


class TestDetailedHealthCheckResponseChar:
    """Characterization: DetailedHealthCheckResponse current behavior"""

    def test_accepts_detailed_health_response(self):
        """CHAR: Valid detailed health response is accepted"""
        now = datetime.now(timezone.utc)
        response = DetailedHealthCheckResponse(
            service="credit_service",
            status="operational",
            port=8229,
            version="1.0.0",
            database_connected=True,
            account_client_available=True,
            subscription_client_available=True,
            expiration_job_healthy=True,
            timestamp=now
        )
        assert response.database_connected is True
        assert response.expiration_job_healthy is True


class TestErrorResponseChar:
    """Characterization: ErrorResponse current behavior"""

    def test_accepts_error_response(self):
        """CHAR: Valid error response is accepted"""
        now = datetime.now(timezone.utc)
        response = ErrorResponse(
            error="ValidationError",
            detail="Invalid credit type",
            timestamp=now
        )
        assert response.error == "ValidationError"
        assert response.detail == "Invalid credit type"


class TestSuccessResponseChar:
    """Characterization: SuccessResponse current behavior"""

    def test_accepts_success_response(self):
        """CHAR: Valid success response is accepted"""
        response = SuccessResponse(
            success=True,
            message="Operation completed successfully"
        )
        assert response.success is True
        assert response.message == "Operation completed successfully"


# =============================================================================
# Additional Validation Tests - Edge Cases
# =============================================================================

class TestBalanceQueryRequestChar:
    """Characterization: BalanceQueryRequest current behavior"""

    def test_accepts_balance_query(self):
        """CHAR: Valid balance query is accepted"""
        request = BalanceQueryRequest(user_id="user_123")
        assert request.user_id == "user_123"


class TestAccountQueryRequestChar:
    """Characterization: AccountQueryRequest current behavior"""

    def test_accepts_minimal_query(self):
        """CHAR: Minimal account query is accepted"""
        request = AccountQueryRequest(user_id="user_123")
        assert request.user_id == "user_123"
        assert request.credit_type is None
        assert request.is_active is None

    def test_accepts_full_query(self):
        """CHAR: Full account query is accepted"""
        request = AccountQueryRequest(
            user_id="user_123",
            credit_type="promotional",
            is_active=True
        )
        assert request.credit_type == "promotional"
        assert request.is_active is True


class TestCreditAccountListResponseChar:
    """Characterization: CreditAccountListResponse current behavior"""

    def test_accepts_account_list(self):
        """CHAR: Valid account list response is accepted"""
        now = datetime.now(timezone.utc)
        accounts = [
            CreditAccountResponse(
                account_id="cred_acc_123",
                user_id="user_123",
                credit_type="promotional",
                balance=5000,
                total_allocated=10000,
                total_consumed=3000,
                total_expired=2000,
                expiration_policy="fixed_days",
                expiration_days=90,
                is_active=True,
                created_at=now,
                updated_at=now
            )
        ]
        response = CreditAccountListResponse(
            accounts=accounts,
            total=1
        )
        assert len(response.accounts) == 1
        assert response.total == 1


class TestNextExpirationChar:
    """Characterization: NextExpiration current behavior"""

    def test_accepts_next_expiration(self):
        """CHAR: Valid next expiration is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        next_exp = NextExpiration(
            amount=2000,
            expires_at=expires
        )
        assert next_exp.amount == 2000
        assert next_exp.expires_at == expires


class TestConsumptionTransactionChar:
    """Characterization: ConsumptionTransaction current behavior"""

    def test_accepts_consumption_transaction(self):
        """CHAR: Valid consumption transaction is accepted"""
        transaction = ConsumptionTransaction(
            transaction_id="cred_txn_123",
            account_id="cred_acc_123",
            amount=500,
            credit_type="promotional"
        )
        assert transaction.transaction_id == "cred_txn_123"
        assert transaction.amount == 500


class TestConsumptionPlanItemChar:
    """Characterization: ConsumptionPlanItem current behavior"""

    def test_accepts_plan_item(self):
        """CHAR: Valid consumption plan item is accepted"""
        expires = datetime.now(timezone.utc) + timedelta(days=90)
        item = ConsumptionPlanItem(
            account_id="cred_acc_123",
            credit_type="promotional",
            amount=1000,
            expires_at=expires
        )
        assert item.account_id == "cred_acc_123"
        assert item.amount == 1000


class TestCreditTransactionResponseChar:
    """Characterization: CreditTransactionResponse current behavior"""

    def test_accepts_transaction_response(self):
        """CHAR: Valid transaction response is accepted"""
        now = datetime.now(timezone.utc)
        response = CreditTransactionResponse(
            transaction_id="cred_txn_123",
            account_id="cred_acc_123",
            user_id="user_123",
            transaction_type="allocate",
            amount=1000,
            balance_before=0,
            balance_after=1000,
            created_at=now
        )
        assert response.transaction_id == "cred_txn_123"
        assert response.amount == 1000

    def test_transaction_response_with_reference(self):
        """CHAR: Transaction response with reference is accepted"""
        now = datetime.now(timezone.utc)
        response = CreditTransactionResponse(
            transaction_id="cred_txn_123",
            account_id="cred_acc_123",
            user_id="user_123",
            transaction_type="consume",
            amount=-500,
            balance_before=1000,
            balance_after=500,
            reference_id="bill_123",
            reference_type="billing",
            description="Usage billing",
            metadata={"session_id": "sess_123"},
            created_at=now
        )
        assert response.reference_id == "bill_123"
        assert response.reference_type == "billing"


class TestTransactionListResponseChar:
    """Characterization: TransactionListResponse current behavior"""

    def test_accepts_transaction_list(self):
        """CHAR: Valid transaction list is accepted"""
        now = datetime.now(timezone.utc)
        transactions = [
            CreditTransactionResponse(
                transaction_id="cred_txn_123",
                account_id="cred_acc_123",
                user_id="user_123",
                transaction_type="allocate",
                amount=1000,
                balance_before=0,
                balance_after=1000,
                created_at=now
            )
        ]
        response = TransactionListResponse(
            transactions=transactions,
            total=1,
            page=1,
            page_size=50
        )
        assert len(response.transactions) == 1
        assert response.total == 1
        assert response.page == 1


class TestCreditTypeBreakdownChar:
    """Characterization: CreditTypeBreakdown current behavior"""

    def test_accepts_type_breakdown(self):
        """CHAR: Valid type breakdown is accepted"""
        breakdown = CreditTypeBreakdown(
            allocated=10000,
            consumed=6000,
            expired=1000
        )
        assert breakdown.allocated == 10000
        assert breakdown.consumed == 6000
        assert breakdown.expired == 1000


# =============================================================================
# Additional Edge Case Tests
# =============================================================================

class TestCreditAccountEdgeCases:
    """Characterization: CreditAccount edge cases"""

    def test_all_expiration_policies_accepted(self):
        """CHAR: All expiration policy enum values are accepted"""
        for policy in ExpirationPolicyEnum:
            account = CreditAccount(
                account_id=f"cred_acc_{policy.value}",
                user_id="user_123",
                credit_type=CreditTypeEnum.PROMOTIONAL,
                expiration_policy=policy,
                expiration_days=90
            )
            assert account.expiration_policy == policy

    def test_all_credit_types_accepted(self):
        """CHAR: All credit type enum values are accepted"""
        for credit_type in CreditTypeEnum:
            account = CreditAccount(
                account_id=f"cred_acc_{credit_type.value}",
                user_id="user_123",
                credit_type=credit_type,
                expiration_policy=ExpirationPolicyEnum.FIXED_DAYS,
                expiration_days=90
            )
            assert account.credit_type == credit_type


class TestCreditTransactionEdgeCases:
    """Characterization: CreditTransaction edge cases"""

    def test_all_transaction_types_accepted(self):
        """CHAR: All transaction type enum values are accepted"""
        for txn_type in TransactionTypeEnum:
            transaction = CreditTransaction(
                transaction_id=f"cred_txn_{txn_type.value}",
                account_id="cred_acc_123",
                user_id="user_123",
                transaction_type=txn_type,
                amount=100 if txn_type in [TransactionTypeEnum.ALLOCATE, TransactionTypeEnum.TRANSFER_IN] else -100,
                balance_before=1000,
                balance_after=1100 if txn_type in [TransactionTypeEnum.ALLOCATE, TransactionTypeEnum.TRANSFER_IN] else 900
            )
            assert transaction.transaction_type == txn_type

    def test_all_reference_types_accepted(self):
        """CHAR: All reference type enum values are accepted"""
        for ref_type in ReferenceTypeEnum:
            transaction = CreditTransaction(
                transaction_id=f"cred_txn_{ref_type.value}",
                account_id="cred_acc_123",
                user_id="user_123",
                transaction_type=TransactionTypeEnum.ALLOCATE,
                amount=1000,
                balance_before=0,
                balance_after=1000,
                reference_id=f"ref_{ref_type.value}_123",
                reference_type=ref_type
            )
            assert transaction.reference_type == ref_type


class TestCreditAllocationEdgeCases:
    """Characterization: CreditAllocation edge cases"""

    def test_all_allocation_statuses_accepted(self):
        """CHAR: All allocation status enum values are accepted"""
        for status in AllocationStatusEnum:
            allocation = CreditAllocation(
                allocation_id=f"cred_alloc_{status.value}",
                account_id="cred_acc_123",
                user_id="user_123",
                amount=1000,
                remaining_balance=1000 if status == AllocationStatusEnum.COMPLETED else 0,
                status=status
            )
            assert allocation.status == status


class TestRequestValidationEdgeCases:
    """Characterization: Request validation edge cases"""

    def test_create_account_max_length_fields(self):
        """CHAR: Max length validation for create account request"""
        # Valid max length user_id
        request = CreateAccountRequest(
            user_id="x" * 50,
            credit_type="promotional"
        )
        assert len(request.user_id) == 50

        # Invalid: exceeds max length
        with pytest.raises(ValidationError):
            CreateAccountRequest(
                user_id="x" * 51,
                credit_type="promotional"
            )

    def test_allocate_credits_description_max_length(self):
        """CHAR: Description max length is 500 characters"""
        # Valid max length
        request = AllocateCreditsRequest(
            user_id="user_123",
            credit_type="bonus",
            amount=1000,
            description="x" * 500
        )
        assert len(request.description) == 500

        # Invalid: exceeds max length
        with pytest.raises(ValidationError):
            AllocateCreditsRequest(
                user_id="user_123",
                credit_type="bonus",
                amount=1000,
                description="x" * 501
            )

    def test_campaign_name_max_length(self):
        """CHAR: Campaign name max length is 100 characters"""
        now = datetime.now(timezone.utc)
        # Valid max length
        request = CreateCampaignRequest(
            name="x" * 100,
            credit_type="promotional",
            credit_amount=1000,
            total_budget=100000,
            start_date=now,
            end_date=now + timedelta(days=30)
        )
        assert len(request.name) == 100

        # Invalid: exceeds max length
        with pytest.raises(ValidationError):
            CreateCampaignRequest(
                name="x" * 101,
                credit_type="promotional",
                credit_amount=1000,
                total_budget=100000,
                start_date=now,
                end_date=now + timedelta(days=30)
            )


class TestResponseDefaultValues:
    """Characterization: Response model default values"""

    def test_health_response_defaults(self):
        """CHAR: DetailedHealthCheckResponse has default values"""
        response = DetailedHealthCheckResponse(
            database_connected=True,
            account_client_available=True,
            subscription_client_available=True,
            expiration_job_healthy=True,
            timestamp=None
        )
        assert response.service == "credit_service"  # Default
        assert response.status == "operational"  # Default
        assert response.port == 8229  # Default
        assert response.version == "1.0.0"  # Default

    def test_account_response_currency_default(self):
        """CHAR: CreditAccountResponse has default currency"""
        now = datetime.now(timezone.utc)
        response = CreditAccountResponse(
            account_id="cred_acc_123",
            user_id="user_123",
            credit_type="promotional",
            balance=5000,
            total_allocated=10000,
            total_consumed=3000,
            total_expired=2000,
            expiration_policy="fixed_days",
            expiration_days=90,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        assert response.currency == "CREDIT"  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
