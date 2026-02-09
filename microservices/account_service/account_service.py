"""
Account Service Business Logic

Account management business logic layer for the microservice.
Handles validation, business rules, and error handling.

Note: Account service is the identity anchor only.
Subscription data is managed by subscription_service.

Design: Uses dependency injection for testability.
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Import protocols (no I/O dependencies)
from .protocols import (
    AccountRepositoryProtocol,
    DuplicateEntryError,
    UserNotFoundError,
)
from .models import (
    AccountEnsureRequest,
    AccountListParams,
    AccountPreferencesRequest,
    AccountProfileResponse,
    AccountSearchParams,
    AccountSearchResponse,
    AccountStatsResponse,
    AccountStatusChangeRequest,
    AccountSummaryResponse,
    AccountUpdateRequest,
    User,
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AccountServiceError(Exception):
    """Base exception for account service errors"""
    pass


class AccountValidationError(AccountServiceError):
    """Account validation error"""
    pass


class AccountNotFoundError(AccountServiceError):
    """Account not found error"""
    pass


class AccountService:
    """
    Account management business logic service

    Handles all account-related business operations while delegating
    data access to the AccountRepository layer.

    Note: This service handles identity data only. For subscription info,
    use the subscription_client to query subscription_service.

    Design: Uses dependency injection for testability.
    - Pass repository=MockRepo for testing
    - Pass repository=None for production (will be created via factory)
    """

    def __init__(
        self,
        repository: Optional[AccountRepositoryProtocol] = None,
        event_bus=None,
        subscription_client=None,
    ):
        """
        Initialize AccountService with injected dependencies.

        Args:
            repository: Account repository (inject mock for testing)
            event_bus: Event bus for publishing events
            subscription_client: Client for subscription service
        """
        self.account_repo = repository  # Will be set by factory if None
        self.event_bus = event_bus
        self.subscription_client = subscription_client
        self._event_publishers_loaded = False

    def _lazy_load_event_publishers(self):
        """Lazy load event publishers to avoid import-time I/O"""
        if not self._event_publishers_loaded:
            try:
                from .events.publishers import (
                    publish_user_created,
                    publish_user_deleted,
                    publish_user_profile_updated,
                    publish_user_status_changed,
                )
                self._publish_user_created = publish_user_created
                self._publish_user_deleted = publish_user_deleted
                self._publish_user_profile_updated = publish_user_profile_updated
                self._publish_user_status_changed = publish_user_status_changed
                self._event_publishers_loaded = True
            except ImportError as e:
                logger.warning(f"Could not load event publishers: {e}")
                self._event_publishers_loaded = True  # Don't retry

    # Account Lifecycle Operations

    async def ensure_account(
        self, request: AccountEnsureRequest
    ) -> Tuple[AccountProfileResponse, bool]:
        """
        Ensure account exists, create if needed

        Args:
            request: Account ensure request

        Returns:
            Tuple of (account_response, was_created)

        Raises:
            AccountValidationError: If request data is invalid
            AccountServiceError: If operation fails
        """
        try:
            self._validate_account_ensure_request(request)

            user = await self.account_repo.ensure_account_exists(
                user_id=request.user_id,
                email=request.email,
                name=request.name,
            )

            account_response = self._user_to_profile_response(user)

            was_created = (
                user.created_at
                and (datetime.now(timezone.utc) - user.created_at).total_seconds() < 60
            )

            if was_created and self.event_bus:
                try:
                    self._lazy_load_event_publishers()
                    # Get subscription tier from subscription_service
                    subscription_plan = "free"  # Default
                    if self.subscription_client:
                        try:
                            # Try to get or create subscription for the new user
                            sub_result = await self.subscription_client.get_or_create_subscription(
                                user_id=request.user_id,
                                tier_code="free"
                            )
                            if sub_result and sub_result.get("subscription"):
                                subscription_plan = sub_result["subscription"].get("tier_code", "free")
                        except Exception as sub_e:
                            logger.warning(f"Failed to get subscription for user {request.user_id}: {sub_e}")

                    if hasattr(self, '_publish_user_created'):
                        await self._publish_user_created(
                            event_bus=self.event_bus,
                            user_id=request.user_id,
                            email=request.email,
                            name=request.name,
                            subscription_plan=subscription_plan,
                        )
                except Exception as e:
                    logger.error(f"Failed to publish user.created event: {e}")

            logger.info(f"Account ensured: {request.user_id}, created: {was_created}")
            return account_response, was_created

        except DuplicateEntryError as e:
            raise AccountValidationError(
                f"Account with email already exists: {request.email}"
            )
        except AccountValidationError:
            # Re-raise validation errors without wrapping
            raise
        except Exception as e:
            logger.error(f"Failed to ensure account: {e}")
            raise AccountServiceError(f"Failed to ensure account: {str(e)}")

    async def get_account_profile(self, user_id: str) -> AccountProfileResponse:
        """
        Get detailed account profile

        Args:
            user_id: User identifier

        Returns:
            Account profile response

        Raises:
            AccountNotFoundError: If account not found
        """
        try:
            user = await self.account_repo.get_account_by_id(user_id)
            if not user:
                raise AccountNotFoundError(f"Account not found: {user_id}")

            return self._user_to_profile_response(user)

        except AccountNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get account profile {user_id}: {e}")
            raise AccountServiceError(f"Failed to get account profile: {str(e)}")

    async def update_account_profile(
        self, user_id: str, request: AccountUpdateRequest
    ) -> AccountProfileResponse:
        """
        Update account profile

        Args:
            user_id: User identifier
            request: Update request

        Returns:
            Updated account profile

        Raises:
            AccountNotFoundError: If account not found
            AccountValidationError: If update data is invalid
        """
        try:
            self._validate_account_update_request(request)

            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.email is not None:
                update_data["email"] = request.email
            if request.preferences is not None:
                update_data["preferences"] = request.preferences

            if not update_data:
                return await self.get_account_profile(user_id)

            updated_user = await self.account_repo.update_account_profile(
                user_id, update_data
            )
            if not updated_user:
                raise AccountNotFoundError(f"Account not found: {user_id}")

            if self.event_bus:
                try:
                    self._lazy_load_event_publishers()
                    if hasattr(self, '_publish_user_profile_updated'):
                        await self._publish_user_profile_updated(
                            event_bus=self.event_bus,
                            user_id=user_id,
                            email=updated_user.email,
                            name=updated_user.name,
                            updated_fields=list(update_data.keys()),
                        )
                except Exception as e:
                    logger.error(f"Failed to publish user.profile_updated event: {e}")

            logger.info(f"Account profile updated: {user_id}")
            return self._user_to_profile_response(updated_user)

        except AccountNotFoundError:
            raise
        except AccountValidationError:
            raise
        except UserNotFoundError as e:
            raise AccountNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Failed to update account profile {user_id}: {e}")
            raise AccountServiceError(f"Failed to update account profile: {str(e)}")

    async def update_account_preferences(
        self, user_id: str, request: AccountPreferencesRequest
    ) -> bool:
        """
        Update account preferences

        Args:
            user_id: User identifier
            request: Preferences update request

        Returns:
            True if successful
        """
        try:
            preferences = {}
            if request.timezone is not None:
                preferences["timezone"] = request.timezone
            if request.language is not None:
                preferences["language"] = request.language
            if request.notification_email is not None:
                preferences["notification_email"] = request.notification_email
            if request.notification_push is not None:
                preferences["notification_push"] = request.notification_push
            if request.theme is not None:
                preferences["theme"] = request.theme

            if not preferences:
                return True

            success = await self.account_repo.update_account_preferences(
                user_id, preferences
            )
            if success:
                logger.info(f"Account preferences updated: {user_id}")
            return success

        except Exception as e:
            logger.error(f"Failed to update account preferences {user_id}: {e}")
            raise AccountServiceError(f"Failed to update account preferences: {str(e)}")

    # Account Status Management

    async def change_account_status(
        self, user_id: str, request: AccountStatusChangeRequest
    ) -> bool:
        """
        Change account status (admin operation)

        Args:
            user_id: User identifier
            request: Status change request

        Returns:
            True if successful
        """
        try:
            user = None
            if self.event_bus:
                try:
                    user = await self.account_repo.get_account_by_id(user_id)
                except Exception:
                    pass

            if request.is_active:
                success = await self.account_repo.activate_account(user_id)
                action = "activated"
            else:
                success = await self.account_repo.deactivate_account(user_id)
                action = "deactivated"

            if success:
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if hasattr(self, '_publish_user_status_changed'):
                            await self._publish_user_status_changed(
                                event_bus=self.event_bus,
                                user_id=user_id,
                                is_active=request.is_active,
                                email=user.email if user else None,
                                reason=request.reason,
                                changed_by="admin",
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to publish user.status_changed event: {e}"
                        )

                logger.info(f"Account {action}: {user_id}, reason: {request.reason}")
            return success

        except Exception as e:
            logger.error(f"Failed to change account status {user_id}: {e}")
            raise AccountServiceError(f"Failed to change account status: {str(e)}")

    async def delete_account(self, user_id: str, reason: Optional[str] = None) -> bool:
        """
        Delete account (soft delete)

        Args:
            user_id: User identifier
            reason: Deletion reason

        Returns:
            True if successful
        """
        try:
            user = None
            if self.event_bus:
                try:
                    user = await self.account_repo.get_account_by_id(user_id)
                except Exception:
                    pass

            success = await self.account_repo.delete_account(user_id)
            if success:
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if hasattr(self, '_publish_user_deleted'):
                            await self._publish_user_deleted(
                                event_bus=self.event_bus,
                                user_id=user_id,
                                email=user.email if user else None,
                                reason=reason,
                            )
                    except Exception as e:
                        logger.error(f"Failed to publish user.deleted event: {e}")

                logger.info(f"Account deleted: {user_id}, reason: {reason}")
            return success

        except Exception as e:
            logger.error(f"Failed to delete account {user_id}: {e}")
            raise AccountServiceError(f"Failed to delete account: {str(e)}")

    # Account Query Operations

    async def list_accounts(self, params: AccountListParams) -> AccountSearchResponse:
        """
        List accounts with filtering and pagination

        Args:
            params: List parameters

        Returns:
            Account search response with pagination
        """
        try:
            users = await self.account_repo.list_accounts(
                limit=params.page_size,
                offset=(params.page - 1) * params.page_size,
                is_active=params.is_active,
                search=params.search,
            )

            accounts = [self._user_to_summary_response(user) for user in users]

            stats = await self.account_repo.get_account_stats()
            total_count = stats.get("total_accounts", 0)
            has_next = len(accounts) == params.page_size

            return AccountSearchResponse(
                accounts=accounts,
                total_count=total_count,
                page=params.page,
                page_size=params.page_size,
                has_next=has_next,
            )

        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise AccountServiceError(f"Failed to list accounts: {str(e)}")

    async def search_accounts(
        self, params: AccountSearchParams
    ) -> List[AccountSummaryResponse]:
        """
        Search accounts by query

        Args:
            params: Search parameters

        Returns:
            List of matching accounts
        """
        try:
            users = await self.account_repo.search_accounts(
                query=params.query, limit=params.limit
            )

            if not params.include_inactive:
                users = [user for user in users if user.is_active]

            return [self._user_to_summary_response(user) for user in users]

        except Exception as e:
            logger.error(f"Failed to search accounts: {e}")
            raise AccountServiceError(f"Failed to search accounts: {str(e)}")

    async def get_account_by_email(
        self, email: str
    ) -> Optional[AccountProfileResponse]:
        """Get account by email address"""
        try:
            user = await self.account_repo.get_account_by_email(email)
            return self._user_to_profile_response(user) if user else None
        except Exception as e:
            logger.error(f"Failed to get account by email {email}: {e}")
            return None

    # Service Operations

    async def get_service_stats(self) -> AccountStatsResponse:
        """Get account service statistics"""
        try:
            stats_data = await self.account_repo.get_account_stats()
            return AccountStatsResponse(**stats_data)
        except Exception as e:
            logger.error(f"Failed to get service stats: {e}")
            raise AccountServiceError(f"Failed to get service stats: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the service"""
        try:
            await self.account_repo.get_account_stats()
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }

    # Private Helper Methods

    def _validate_account_ensure_request(self, request: AccountEnsureRequest) -> None:
        """Validate account ensure request"""
        if not request.user_id or not request.user_id.strip():
            raise AccountValidationError("user_id is required")
        if not request.email or not request.email.strip():
            raise AccountValidationError("email is required")
        if not request.name or not request.name.strip():
            raise AccountValidationError("name is required")

        # Validate email format - reject whitespace characters
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", request.email):
            raise AccountValidationError("Invalid email format")

    def _validate_account_update_request(self, request: AccountUpdateRequest) -> None:
        """Validate account update request"""
        if request.name is not None and not request.name.strip():
            raise AccountValidationError("name cannot be empty")
        if request.email is not None and not re.match(
            r"^[^\s@]+@[^\s@]+\.[^\s@]+$", request.email
        ):
            raise AccountValidationError("Invalid email format")

    def _user_to_profile_response(self, user: User) -> AccountProfileResponse:
        """Convert User model to AccountProfileResponse"""
        return AccountProfileResponse(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            preferences=getattr(user, "preferences", {}),
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _user_to_summary_response(self, user: User) -> AccountSummaryResponse:
        """Convert User model to AccountSummaryResponse"""
        return AccountSummaryResponse(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
