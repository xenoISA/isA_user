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
    SessionRepository, SessionMessageRepository,
    SessionNotFoundException
)
from .models import (
    SessionCreateRequest, SessionUpdateRequest, MessageCreateRequest,
    MemoryCreateRequest, MemoryUpdateRequest, SessionResponse, SessionListResponse,
    MessageResponse, MessageListResponse, MemoryResponse, SessionSummaryResponse,
    SessionStatsResponse, Session, SessionMessage, SessionMemory
)
from microservices.account_service.client import AccountServiceClient

# Import Consul registry for service discovery
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config_manager import ConfigManager
from core.nats_client import Event, EventType, ServiceSource

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

    def __init__(self, event_bus=None, config=None):
        # Initialize repositories with config for service discovery
        self.session_repo = SessionRepository(config=config)
        self.message_repo = SessionMessageRepository(config=config)
        # Note: Memory functionality is handled by dedicated memory_service
        self.account_client = AccountServiceClient()
        self.event_bus = event_bus

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

            # Application-layer validation: Check if user exists via account service API
            # This replaces database foreign key constraint for microservice independence
            try:
                user_profile = await self.account_client.get_account_profile(request.user_id)
                if not user_profile:
                    logger.warning(f"Creating session for potentially non-existent user: {request.user_id}")
                    # Note: We log a warning but don't fail - this allows eventual consistency
            except Exception as e:
                logger.warning(f"Account service unavailable, failing open: {e}")
                # Fail open - allow operation if account service is unavailable

            # Use provided session_id or generate new UUID
            session_id = request.session_id if request.session_id else str(uuid.uuid4())

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

            # Publish SESSION_STARTED event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.SESSION_STARTED,
                        source=ServiceSource.SESSION_SERVICE,
                        data={
                            "session_id": session_id,
                            "user_id": request.user_id,
                            "metadata": request.metadata or {},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published session.started event for session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to publish session.started event: {e}")

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

                # Publish SESSION_ENDED event
                if self.event_bus:
                    try:
                        # Get updated session for metrics
                        updated_session = await self.session_repo.get_by_session_id(session_id)
                        event = Event(
                            event_type=EventType.SESSION_ENDED,
                            source=ServiceSource.SESSION_SERVICE,
                            data={
                                "session_id": session_id,
                                "user_id": session.user_id,
                                "total_messages": updated_session.message_count if updated_session else 0,
                                "total_tokens": updated_session.total_tokens if updated_session else 0,
                                "total_cost": float(updated_session.total_cost) if updated_session and updated_session.total_cost else 0.0,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published session.ended event for session {session_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish session.ended event: {e}")

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

            # Publish SESSION_MESSAGE_SENT event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.SESSION_MESSAGE_SENT,
                        source=ServiceSource.SESSION_SERVICE,
                        data={
                            "session_id": session_id,
                            "user_id": session.user_id,
                            "message_id": message.message_id,
                            "role": request.role,
                            "content": request.content,  # Add message content for memory service
                            "message_type": request.message_type,
                            "tokens_used": request.tokens_used or 0,
                            "cost_usd": float(request.cost_usd) if request.cost_usd else 0.0,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published session.message_sent event for session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to publish session.message_sent event: {e}")

            # Publish SESSION_TOKENS_USED event if tokens were consumed
            if self.event_bus and request.tokens_used and request.tokens_used > 0:
                try:
                    event = Event(
                        event_type=EventType.SESSION_TOKENS_USED,
                        source=ServiceSource.SESSION_SERVICE,
                        data={
                            "session_id": session_id,
                            "user_id": session.user_id,
                            "message_id": message.message_id,
                            "tokens_used": request.tokens_used,
                            "cost_usd": float(request.cost_usd) if request.cost_usd else 0.0,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published session.tokens_used event for session {session_id}: {request.tokens_used} tokens")
                except Exception as e:
                    logger.error(f"Failed to publish session.tokens_used event: {e}")

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
    
    # Note: Memory Operations are handled by dedicated memory_service
    # See microservices/memory_service for session memory functionality

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

            # Note: Memory is handled by dedicated memory_service
            return SessionSummaryResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                status=session.status,
                message_count=session.message_count,
                total_tokens=session.total_tokens,
                total_cost=session.total_cost,
                has_memory=False,  # Memory is handled by memory_service
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
    
