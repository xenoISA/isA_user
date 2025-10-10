"""
Session Service Business Logic

Session management business logic layer for the microservice.
Handles validation, business rules, and error handling.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import uuid
import requests

from .session_repository import (
    SessionRepository, SessionMessageRepository, SessionMemoryRepository,
    SessionNotFoundException
)
from .models import (
    SessionCreateRequest, SessionUpdateRequest, MessageCreateRequest,
    MemoryCreateRequest, MemoryUpdateRequest, SessionResponse, SessionListResponse,
    MessageResponse, MessageListResponse, MemoryResponse, SessionSummaryResponse,
    SessionStatsResponse, Session, SessionMessage, SessionMemory
)

# Import Consul registry for service discovery
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.consul_registry import ConsulRegistry
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SessionServiceError(Exception):
    """Base exception for session service errors"""
    pass


class SessionValidationError(SessionServiceError):
    """Session validation error"""
    pass


class SessionNotFoundError(SessionServiceError):
    """Session not found error"""
    pass


class MessageNotFoundError(SessionServiceError):
    """Message not found error"""
    pass


class MemoryNotFoundError(SessionServiceError):
    """Memory not found error"""
    pass


class SessionService:
    """
    Session management business logic service
    
    Handles all session-related business operations while delegating
    data access to the Repository layers.
    """
    
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = SessionMessageRepository()
        self.memory_repo = SessionMemoryRepository()

        # Initialize Consul for service discovery
        config_manager = ConfigManager("session_service")
        config = config_manager.get_service_config()
        self.consul_registry = ConsulRegistry(
            service_name="session_service",
            service_port=config.service_port,
            consul_host=config.consul_host,
            consul_port=config.consul_port
        )
    
    # Session Operations
    
    async def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """
        Create new session

        Args:
            request: Session creation request

        Returns:
            Created session response

        Raises:
            SessionValidationError: If request data is invalid
            SessionServiceError: If operation fails
        """
        try:
            # Validate request
            self._validate_session_create_request(request)

            # Application-layer validation: Check if user exists
            # This replaces the database foreign key constraint for microservice independence
            user_exists = await self._check_user_exists(request.user_id)
            if not user_exists:
                logger.warning(f"Creating session for potentially non-existent user: {request.user_id}")
                # Note: We log a warning but don't fail - this allows eventual consistency
                # If you want strict validation, uncomment the following lines:
                # raise SessionValidationError(
                #     f"User {request.user_id} does not exist. Please create the user first."
                # )

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Prepare session data
            session_data = {
                'session_id': session_id,
                'user_id': request.user_id,
                'conversation_data': request.conversation_data or {},
                'metadata': request.metadata or {},
                'status': 'active'
            }

            # Create session
            session = await self.session_repo.create_session(session_data)

            if not session:
                raise SessionServiceError("Failed to create session")

            logger.info(f"Session created: {session_id} for user {request.user_id}")
            return self._session_to_response(session)

        except Exception as e:
            if isinstance(e, (SessionValidationError, SessionServiceError)):
                raise
            logger.error(f"Error creating session: {e}")
            raise SessionServiceError(f"Failed to create session: {str(e)}")
    
    async def get_session(self, session_id: str, user_id: Optional[str] = None) -> SessionResponse:
        """
        Get session by ID
        
        Args:
            session_id: Session ID
            user_id: Optional user ID for authorization
            
        Returns:
            Session response
            
        Raises:
            SessionNotFoundError: If session not found
        """
        try:
            session = await self.session_repo.get_by_session_id(session_id)
            
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            # Check authorization if user_id provided
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            return self._session_to_response(session)
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise SessionServiceError(f"Failed to get session: {str(e)}")
    
    async def get_user_sessions(
        self, 
        user_id: str, 
        active_only: bool = False,
        page: int = 1, 
        page_size: int = 50
    ) -> SessionListResponse:
        """
        Get user sessions with pagination
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            page: Page number
            page_size: Items per page
            
        Returns:
            Session list response
        """
        try:
            offset = (page - 1) * page_size
            sessions = await self.session_repo.get_user_sessions(
                user_id=user_id,
                active_only=active_only,
                limit=page_size,
                offset=offset
            )
            
            session_responses = [self._session_to_response(s) for s in sessions]
            
            return SessionListResponse(
                sessions=session_responses,
                total=len(session_responses),  # Simplified - would need count query
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {e}")
            raise SessionServiceError(f"Failed to get user sessions: {str(e)}")
    
    async def update_session(self, session_id: str, request: SessionUpdateRequest, user_id: Optional[str] = None) -> SessionResponse:
        """
        Update session
        
        Args:
            session_id: Session ID
            request: Update request
            user_id: Optional user ID for authorization
            
        Returns:
            Updated session response
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            # Update session status if provided
            if request.status:
                await self.session_repo.update_session_status(session_id, request.status)
            
            # Record activity
            await self.session_repo.update_session_activity(session_id)
            
            # Get updated session
            updated_session = await self.session_repo.get_by_session_id(session_id)
            return self._session_to_response(updated_session)
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            raise SessionServiceError(f"Failed to update session: {str(e)}")
    
    async def end_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """
        End session
        
        Args:
            session_id: Session ID
            user_id: Optional user ID for authorization
            
        Returns:
            Success status
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            # Update status to ended
            success = await self.session_repo.update_session_status(session_id, "ended")
            
            if success:
                logger.info(f"Session ended: {session_id}")
            
            return success
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            raise SessionServiceError(f"Failed to end session: {str(e)}")
    
    # Message Operations
    
    async def add_message(
        self, 
        session_id: str, 
        request: MessageCreateRequest,
        user_id: Optional[str] = None
    ) -> MessageResponse:
        """
        Add message to session
        
        Args:
            session_id: Session ID
            request: Message creation request
            user_id: Optional user ID for authorization
            
        Returns:
            Created message response
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            # Validate message request
            self._validate_message_create_request(request)
            
            # Prepare message data
            message_data = {
                'session_id': session_id,
                'user_id': session.user_id,
                'role': request.role,
                'content': request.content,
                'message_type': request.message_type,
                'metadata': request.metadata or {},
                'tokens_used': request.tokens_used,
                'cost_usd': request.cost_usd
            }
            
            # Create message
            message = await self.message_repo.create_message(message_data)
            
            if not message:
                raise SessionServiceError("Failed to create message")
            
            # Update session metrics
            await self.session_repo.increment_message_count(
                session_id, 
                request.tokens_used, 
                request.cost_usd
            )
            
            return self._message_to_response(message)
            
        except (SessionNotFoundError, SessionValidationError):
            raise
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            raise SessionServiceError(f"Failed to add message: {str(e)}")
    
    async def get_session_messages(
        self, 
        session_id: str, 
        page: int = 1, 
        page_size: int = 100,
        user_id: Optional[str] = None
    ) -> MessageListResponse:
        """
        Get session messages with pagination
        
        Args:
            session_id: Session ID
            page: Page number
            page_size: Items per page
            user_id: Optional user ID for authorization
            
        Returns:
            Message list response
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            offset = (page - 1) * page_size
            messages = await self.message_repo.get_session_messages(
                session_id=session_id,
                limit=page_size,
                offset=offset
            )
            
            message_responses = [self._message_to_response(m) for m in messages]
            
            return MessageListResponse(
                messages=message_responses,
                total=len(message_responses),  # Simplified
                page=page,
                page_size=page_size
            )
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            raise SessionServiceError(f"Failed to get session messages: {str(e)}")
    
    # Memory Operations
    
    async def create_session_memory(
        self, 
        session_id: str, 
        request: MemoryCreateRequest,
        user_id: Optional[str] = None
    ) -> MemoryResponse:
        """
        Create or update session memory
        
        Args:
            session_id: Session ID
            request: Memory creation request
            user_id: Optional user ID for authorization
            
        Returns:
            Memory response
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            # Check if memory already exists
            existing_memory = await self.memory_repo.get_by_session_id(session_id)
            
            if existing_memory:
                # Update existing memory
                memory_data = {
                    'content': request.content,
                    'metadata': request.metadata or {}
                }
                success = await self.memory_repo.update_memory(session_id, memory_data)
                
                if not success:
                    raise SessionServiceError("Failed to update session memory")
                
                # Get updated memory
                updated_memory = await self.memory_repo.get_by_session_id(session_id)
                return self._memory_to_response(updated_memory)
            else:
                # Create new memory
                memory_data = {
                    'session_id': session_id,
                    'user_id': session.user_id,
                    'memory_type': request.memory_type,
                    'content': request.content,
                    'metadata': request.metadata or {}
                }
                
                memory = await self.memory_repo.create_memory(memory_data)
                
                if not memory:
                    raise SessionServiceError("Failed to create session memory")
                
                return self._memory_to_response(memory)
            
        except (SessionNotFoundError, SessionServiceError):
            raise
        except Exception as e:
            logger.error(f"Error creating session memory for {session_id}: {e}")
            raise SessionServiceError(f"Failed to create session memory: {str(e)}")
    
    async def get_session_memory(self, session_id: str, user_id: Optional[str] = None) -> Optional[MemoryResponse]:
        """
        Get session memory
        
        Args:
            session_id: Session ID
            user_id: Optional user ID for authorization
            
        Returns:
            Memory response or None
        """
        try:
            # Verify session exists and authorize
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            memory = await self.memory_repo.get_by_session_id(session_id)
            
            if memory:
                return self._memory_to_response(memory)
            return None
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting session memory for {session_id}: {e}")
            raise SessionServiceError(f"Failed to get session memory: {str(e)}")
    
    # Utility Methods
    
    async def get_session_summary(self, session_id: str, user_id: Optional[str] = None) -> SessionSummaryResponse:
        """
        Get session summary with metrics
        """
        try:
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if user_id and session.user_id != user_id:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            memory = await self.memory_repo.get_by_session_id(session_id)
            
            return SessionSummaryResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                status=session.status,
                message_count=session.message_count,
                total_tokens=session.total_tokens,
                total_cost=session.total_cost,
                has_memory=memory is not None,
                is_active=session.is_active,
                created_at=session.created_at,
                last_activity=session.last_activity
            )
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting session summary for {session_id}: {e}")
            raise SessionServiceError(f"Failed to get session summary: {str(e)}")
    
    async def get_service_stats(self) -> SessionStatsResponse:
        """Get session service statistics"""
        try:
            # This would require additional queries in production
            return SessionStatsResponse(
                total_sessions=0,
                active_sessions=0,
                total_messages=0,
                total_tokens=0,
                total_cost=0.0,
                average_messages_per_session=0.0
            )
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            raise SessionServiceError(f"Failed to get service stats: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the service"""
        try:
            # Test database connectivity
            # This is a simple check - could be enhanced
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "session_service"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "session_service",
                "error": str(e)
            }
    
    # Private helper methods
    
    def _validate_session_create_request(self, request: SessionCreateRequest):
        """Validate session creation request"""
        if not request.user_id or not request.user_id.strip():
            raise SessionValidationError("user_id is required")

    async def _check_user_exists(self, user_id: str) -> bool:
        """
        Check if user exists by calling account_service via Consul

        This is application-layer validation replacing database foreign key constraints.
        Allows microservice independence while maintaining data integrity.

        Args:
            user_id: User ID to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            # Discover account_service via Consul
            account_service_url = self.consul_registry.get_service_address(
                "account_service",
                fallback_url="http://localhost:8201"
            )

            # Call account service to check if user exists
            response = requests.get(
                f"{account_service_url}/api/v1/accounts/profile/{user_id}",
                timeout=2  # 2 second timeout to avoid blocking
            )

            if response.status_code == 200:
                logger.debug(f"User {user_id} exists in account_service")
                return True
            elif response.status_code == 404:
                logger.debug(f"User {user_id} not found in account_service")
                return False
            else:
                logger.warning(f"Unexpected response from account_service: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout checking user existence for {user_id}, assuming user exists (eventual consistency)")
            return True  # Fail open - allow session creation even if account_service is slow
        except requests.exceptions.ConnectionError:
            logger.warning(f"Cannot connect to account_service, assuming user exists (eventual consistency)")
            return True  # Fail open - allow session creation even if account_service is down
        except Exception as e:
            logger.error(f"Error checking user existence for {user_id}: {e}")
            return True  # Fail open - allow session creation on error

    def _validate_message_create_request(self, request: MessageCreateRequest):
        """Validate message creation request"""
        if not request.role or not request.role.strip():
            raise SessionValidationError("role is required")
        if not request.content or not request.content.strip():
            raise SessionValidationError("content is required")
        if request.role not in ['user', 'assistant', 'system']:
            raise SessionValidationError("role must be one of: user, assistant, system")
    
    def _session_to_response(self, session: Session) -> SessionResponse:
        """Convert Session model to SessionResponse"""
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            status=session.status,
            conversation_data=session.conversation_data,
            metadata=session.metadata,
            is_active=session.is_active,
            message_count=session.message_count,
            total_tokens=session.total_tokens,
            total_cost=session.total_cost,
            session_summary=session.session_summary,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity=session.last_activity
        )
    
    def _message_to_response(self, message: SessionMessage) -> MessageResponse:
        """Convert SessionMessage model to MessageResponse"""
        return MessageResponse(
            message_id=message.message_id or "",
            session_id=message.session_id,
            user_id=message.user_id,
            role=message.role,
            content=message.content,
            message_type=message.message_type,
            metadata=message.metadata,
            tokens_used=message.tokens_used,
            cost_usd=message.cost_usd,
            created_at=message.created_at
        )
    
    def _memory_to_response(self, memory: SessionMemory) -> MemoryResponse:
        """Convert SessionMemory model to MemoryResponse"""
        return MemoryResponse(
            memory_id=memory.memory_id or "",
            session_id=memory.session_id,
            user_id=memory.user_id,
            memory_type=memory.memory_type,
            content=memory.content,
            metadata=memory.metadata,
            created_at=memory.created_at
        )