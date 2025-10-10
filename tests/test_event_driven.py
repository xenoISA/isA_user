"""
Test Event-Driven Architecture with NATS JetStream
Scenario: Payment completed -> Notification + Audit
"""
import asyncio
import logging
from datetime import datetime
from core.nats_client import (
    NATSEventBus, Event, EventType, ServiceSource,
    publish_payment_event
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotificationService:
    """Simulated notification service"""
    def __init__(self):
        self.event_bus = None
    
    async def start(self):
        """Start notification service"""
        self.event_bus = NATSEventBus("notification_service")
        await self.event_bus.connect()
        
        # Subscribe to payment events
        await self.event_bus.subscribe_to_events(
            "payment_service.payment.*",
            self.handle_payment_event
        )
        
        logger.info("NotificationService started and listening for payment events")
    
    async def handle_payment_event(self, event: Event):
        """Handle payment events"""
        logger.info(f"[NotificationService] Received event: {event.type} from {event.source}")
        logger.info(f"[NotificationService] Event data: {event.data}")
        
        # Simulate sending notification
        if event.type == EventType.PAYMENT_COMPLETED.value:
            user_id = event.data.get('user_id')
            amount = event.data.get('amount')
            logger.info(f"[NotificationService] 📧 Sending email to user {user_id}: Payment of ${amount} completed successfully!")
            
            # Publish notification sent event
            notification_event = Event(
                event_type=EventType.NOTIFICATION_SENT,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data={
                    "type": "email",
                    "recipient": user_id,
                    "subject": "Payment Confirmation",
                    "payment_id": event.data.get('payment_id'),
                    "sent_at": datetime.utcnow().isoformat()
                }
            )
            await self.event_bus.publish_event(notification_event)


class AuditService:
    """Simulated audit service"""
    def __init__(self):
        self.event_bus = None
    
    async def start(self):
        """Start audit service"""
        self.event_bus = NATSEventBus("audit_service")
        await self.event_bus.connect()
        
        # Subscribe to all events for auditing
        await self.event_bus.subscribe_to_events(
            "*.*",  # Listen to all events from all services
            self.handle_event
        )
        
        logger.info("AuditService started and listening for all events")
    
    async def handle_event(self, event: Event):
        """Handle all events for audit logging"""
        logger.info(f"[AuditService] 📝 Audit Log: {event.type} from {event.source} at {event.timestamp}")
        logger.info(f"[AuditService] Event ID: {event.id}, Data: {event.data}")


async def simulate_payment_flow():
    """Simulate a payment flow"""
    # Wait for services to be ready
    await asyncio.sleep(2)
    
    logger.info("\n" + "="*50)
    logger.info("Starting Payment Flow Simulation")
    logger.info("="*50 + "\n")
    
    # Step 1: Payment initiated
    logger.info("Step 1: Publishing PAYMENT_INITIATED event")
    await publish_payment_event(
        payment_id="pay-12345",
        amount=99.99,
        status="initiated",
        user_id="user-789",
        metadata={"product": "Premium Subscription"}
    )
    
    await asyncio.sleep(2)
    
    # Step 2: Payment completed
    logger.info("\nStep 2: Publishing PAYMENT_COMPLETED event")
    await publish_payment_event(
        payment_id="pay-12345",
        amount=99.99,
        status="completed",
        user_id="user-789",
        metadata={"product": "Premium Subscription", "transaction_id": "txn-67890"}
    )
    
    await asyncio.sleep(2)
    
    logger.info("\n" + "="*50)
    logger.info("Payment Flow Simulation Completed")
    logger.info("="*50)


async def main():
    """Main function"""
    try:
        # Start services
        notification_service = NotificationService()
        audit_service = AuditService()
        
        # Start services concurrently
        await asyncio.gather(
            notification_service.start(),
            audit_service.start()
        )
        
        # Run payment simulation
        await simulate_payment_flow()
        
        # Keep running for a bit to see all events
        await asyncio.sleep(5)
        
        # Cleanup
        await notification_service.event_bus.close()
        await audit_service.event_bus.close()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())