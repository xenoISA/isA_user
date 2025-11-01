"""
Calendar Service Integration Example

示例：如何在其他服务中集成Calendar Service
"""

import asyncio
from datetime import datetime, timedelta
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from microservices.calendar_service.client import CalendarServiceClient


async def example_calendar_integration():
    """示例：完整的日历服务集成流程"""
    
    # Initialize client
    # Option 1: Use service discovery (auto-detect from Consul)
    client = CalendarServiceClient()
    
    # Option 2: Use explicit URL
    # client = CalendarServiceClient("http://localhost:8240")
    
    try:
        # 1. Health Check
        print("=" * 60)
        print("1. Health Check")
        print("=" * 60)
        healthy = await client.health_check()
        print(f"Service healthy: {healthy}\n")
        
        if not healthy:
            print("Calendar service is not available!")
            return
        
        # 2. Create Event
        print("=" * 60)
        print("2. Create Calendar Event")
        print("=" * 60)
        
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)
        
        event = await client.create_event(
            user_id="user_123",
            title="Team Standup Meeting",
            description="Daily team sync meeting",
            location="Conference Room A",
            start_time=start_time,
            end_time=end_time,
            category="meeting",
            reminders=[15, 60],  # 15 min and 1 hour before
            metadata={"meeting_type": "standup", "team": "engineering"}
        )
        
        if event:
            print(f"✓ Created event: {event['event_id']}")
            print(f"  Title: {event['title']}")
            print(f"  Time: {event['start_time']} - {event['end_time']}")
            event_id = event['event_id']
        else:
            print("✗ Failed to create event")
            return
        
        print()
        
        # 3. Get Event Details
        print("=" * 60)
        print("3. Get Event Details")
        print("=" * 60)
        
        event_details = await client.get_event(event_id, user_id="user_123")
        if event_details:
            print(f"✓ Event found: {event_details['title']}")
            print(f"  Category: {event_details['category']}")
            print(f"  Location: {event_details.get('location', 'N/A')}")
        
        print()
        
        # 4. Create Multiple Events
        print("=" * 60)
        print("4. Create Multiple Events")
        print("=" * 60)
        
        events_to_create = [
            {
                "title": "Project Planning",
                "start_time": tomorrow.replace(hour=14, minute=0),
                "end_time": tomorrow.replace(hour=15, minute=30),
                "category": "work"
            },
            {
                "title": "Code Review",
                "start_time": tomorrow.replace(hour=16, minute=0),
                "end_time": tomorrow.replace(hour=17, minute=0),
                "category": "work"
            },
            {
                "title": "Dentist Appointment",
                "start_time": (tomorrow + timedelta(days=1)).replace(hour=9, minute=0),
                "end_time": (tomorrow + timedelta(days=1)).replace(hour=10, minute=0),
                "category": "personal"
            }
        ]
        
        for event_data in events_to_create:
            created = await client.create_event(
                user_id="user_123",
                **event_data
            )
            if created:
                print(f"✓ Created: {created['title']}")
        
        print()
        
        # 5. List All Events
        print("=" * 60)
        print("5. List All User Events")
        print("=" * 60)
        
        all_events = await client.list_events(
            user_id="user_123",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )
        
        if all_events:
            print(f"✓ Found {all_events['total']} events")
            for evt in all_events['events']:
                print(f"  - {evt['title']} ({evt['category']})")
        
        print()
        
        # 6. Get Upcoming Events
        print("=" * 60)
        print("6. Get Upcoming Events (Next 7 Days)")
        print("=" * 60)
        
        upcoming = await client.get_upcoming_events(user_id="user_123", days=7)
        if upcoming:
            print(f"✓ Found {len(upcoming)} upcoming events:")
            for evt in upcoming:
                print(f"  - {evt['title']} at {evt['start_time']}")
        
        print()
        
        # 7. Get Today's Events
        print("=" * 60)
        print("7. Get Today's Events")
        print("=" * 60)
        
        today_events = await client.get_today_events(user_id="user_123")
        if today_events:
            print(f"✓ Found {len(today_events)} events today:")
            for evt in today_events:
                print(f"  - {evt['title']}")
        else:
            print("  No events today")
        
        print()
        
        # 8. Update Event
        print("=" * 60)
        print("8. Update Event")
        print("=" * 60)
        
        updated = await client.update_event(
            event_id=event_id,
            user_id="user_123",
            title="Team Standup (Updated)",
            location="Virtual - Zoom",
            color="#FF5733"
        )
        
        if updated:
            print(f"✓ Updated event: {updated['title']}")
            print(f"  New location: {updated['location']}")
        
        print()
        
        # 9. Filter by Category
        print("=" * 60)
        print("9. Filter Events by Category")
        print("=" * 60)
        
        work_events = await client.list_events(
            user_id="user_123",
            category="work"
        )
        
        if work_events:
            print(f"✓ Found {work_events['total']} work events:")
            for evt in work_events['events']:
                print(f"  - {evt['title']}")
        
        print()
        
        # 10. External Calendar Sync (Example)
        print("=" * 60)
        print("10. External Calendar Sync Status")
        print("=" * 60)
        
        sync_status = await client.get_sync_status(user_id="user_123")
        if sync_status:
            print(f"✓ Sync status: {sync_status}")
        else:
            print("  No sync configured yet")
        
        print()
        
        # 11. Delete Event
        print("=" * 60)
        print("11. Delete Event")
        print("=" * 60)
        
        deleted = await client.delete_event(event_id, user_id="user_123")
        if deleted:
            print(f"✓ Deleted event: {event_id}")
        
        print()
        
    finally:
        # Clean up
        await client.close()


async def example_task_service_integration():
    """示例：Task Service 如何使用 Calendar Service"""
    
    print("\n" + "=" * 60)
    print("Example: Task Service + Calendar Service")
    print("=" * 60 + "\n")
    
    calendar = CalendarServiceClient()
    
    try:
        # When creating a task with a due date, also create a calendar event
        task_due_date = datetime.now() + timedelta(days=3)
        
        # Create calendar event for task deadline
        event = await calendar.create_event(
            user_id="user_123",
            title="Task Deadline: Complete Report",
            description="Task: Finish quarterly report",
            start_time=task_due_date.replace(hour=9, minute=0),
            end_time=task_due_date.replace(hour=9, minute=30),
            category="work",
            reminders=[60, 1440],  # 1 hour and 1 day before
            metadata={"task_id": "task_456", "type": "deadline"}
        )
        
        if event:
            print(f"✓ Created calendar event for task deadline")
            print(f"  Event ID: {event['event_id']}")
            print(f"  Deadline: {event['start_time']}")
        
    finally:
        await calendar.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Calendar Service Integration Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    asyncio.run(example_calendar_integration())
    asyncio.run(example_task_service_integration())
    
    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60 + "\n")

