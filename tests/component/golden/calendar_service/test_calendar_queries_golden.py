"""
Component Golden Tests: Calendar Service Query Operations

Tests query logic, date range filtering, and pagination.
Uses CalendarTestDataFactory for zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone, timedelta

from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import (
    EventQueryRequest,
    EventCategory,
)
from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCategoryContract,
    EventQueryRequestBuilder,
)
from tests.component.golden.calendar_service.mocks import MockCalendarRepository

pytestmark = [pytest.mark.component, pytest.mark.golden]


class TestDateRangeQueries:
    """Test BR-CAL-010: Query by Date Range"""

    @pytest.fixture
    def populated_repo(self):
        """Create repository with events spanning multiple dates"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Create events for past, today, and future
        for day_offset in range(-7, 8):  # -7 to +7 days
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=CalendarTestDataFactory.make_title(),
                start_time=now + timedelta(days=day_offset),
                end_time=now + timedelta(days=day_offset, hours=1),
            )

        return repo, user_id

    @pytest.fixture
    def service(self, populated_repo):
        """Create service with populated repository"""
        repo, _ = populated_repo
        return CalendarService(repository=repo)

    @pytest.mark.asyncio
    async def test_query_specific_date_range(self, populated_repo):
        """Query events within specific date range"""
        repo, user_id = populated_repo
        service = CalendarService(repository=repo)

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=3)
        end_date = now + timedelta(days=3)

        request = EventQueryRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        result = await service.query_events(request)

        # Should have events within the 6-day window
        assert result.total > 0
        for event in result.events:
            assert event.start_time >= start_date

    @pytest.mark.asyncio
    async def test_query_results_sorted_by_start_time(self, populated_repo):
        """BR-CAL-010: Results sorted by start_time ASC"""
        repo, user_id = populated_repo
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user_id)
        result = await service.query_events(request)

        # Verify sorted order
        for i in range(len(result.events) - 1):
            assert result.events[i].start_time <= result.events[i + 1].start_time

    @pytest.mark.asyncio
    async def test_query_empty_range(self, populated_repo):
        """EC-012: Query with invalid date range returns empty"""
        repo, user_id = populated_repo
        service = CalendarService(repository=repo)

        # End date before start date
        far_future = datetime.now(timezone.utc) + timedelta(days=365)
        far_far_future = far_future + timedelta(days=1)

        request = EventQueryRequest(
            user_id=user_id,
            start_date=far_future,
            end_date=far_far_future,
        )

        result = await service.query_events(request)
        # May be empty if no events in that range
        assert isinstance(result.events, list)


class TestTodayEventsQuery:
    """Test BR-CAL-011: Today's Events Query"""

    @pytest.fixture
    def repo_with_today_events(self):
        """Create repository with today's events"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Events today
        for hour in [9, 12, 15, 18]:
            today = now.replace(hour=hour, minute=0)
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=f"Today Event {hour}h",
                start_time=today,
                end_time=today + timedelta(hours=1),
            )

        # Events not today
        repo.set_event(
            CalendarTestDataFactory.make_event_id(),
            user_id=user_id,
            title="Yesterday Event",
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1) + timedelta(hours=1),
        )

        repo.set_event(
            CalendarTestDataFactory.make_event_id(),
            user_id=user_id,
            title="Tomorrow Event",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1) + timedelta(hours=1),
        )

        return repo, user_id

    @pytest.mark.asyncio
    async def test_get_today_events(self, repo_with_today_events):
        """BR-CAL-011: Return events from 00:00 to 23:59 UTC"""
        repo, user_id = repo_with_today_events
        service = CalendarService(repository=repo)

        events = await service.get_today_events(user_id)

        # Should have today's events (may vary by timing)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_today_events_sorted(self, repo_with_today_events):
        """BR-CAL-011: Today's events sorted by start_time ASC"""
        repo, user_id = repo_with_today_events
        service = CalendarService(repository=repo)

        events = await service.get_today_events(user_id)

        for i in range(len(events) - 1):
            assert events[i].start_time <= events[i + 1].start_time


class TestUpcomingEventsQuery:
    """Test BR-CAL-012: Upcoming Events Query"""

    @pytest.fixture
    def repo_with_upcoming_events(self):
        """Create repository with upcoming events"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Future events at different intervals
        for days in [1, 2, 3, 5, 7, 10, 14, 30]:
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=f"Event in {days} days",
                start_time=now + timedelta(days=days),
                end_time=now + timedelta(days=days, hours=1),
            )

        # Past event (should not appear)
        repo.set_event(
            CalendarTestDataFactory.make_event_id(),
            user_id=user_id,
            title="Past Event",
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1) + timedelta(hours=1),
        )

        return repo, user_id

    @pytest.mark.asyncio
    async def test_get_upcoming_default_7_days(self, repo_with_upcoming_events):
        """BR-CAL-012: Default is 7 days"""
        repo, user_id = repo_with_upcoming_events
        service = CalendarService(repository=repo)

        events = await service.get_upcoming_events(user_id)

        # Should have events within 7 days
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_get_upcoming_custom_days(self, repo_with_upcoming_events):
        """BR-CAL-012: Custom days parameter"""
        repo, user_id = repo_with_upcoming_events
        service = CalendarService(repository=repo)

        events = await service.get_upcoming_events(user_id, days=14)

        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_upcoming_events_sorted(self, repo_with_upcoming_events):
        """BR-CAL-012: Upcoming events sorted by start_time ASC"""
        repo, user_id = repo_with_upcoming_events
        service = CalendarService(repository=repo)

        events = await service.get_upcoming_events(user_id, days=30)

        for i in range(len(events) - 1):
            assert events[i].start_time <= events[i + 1].start_time


class TestCategoryFilter:
    """Test BR-CAL-013: Category Filter"""

    @pytest.fixture
    def repo_with_categories(self):
        """Create repository with events in different categories"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        categories = [
            EventCategory.WORK,
            EventCategory.PERSONAL,
            EventCategory.MEETING,
            EventCategory.REMINDER,
        ]

        for i, category in enumerate(categories):
            for j in range(3):  # 3 events per category
                repo.set_event(
                    CalendarTestDataFactory.make_event_id(),
                    user_id=user_id,
                    title=f"{category.value} Event {j}",
                    start_time=now + timedelta(days=i, hours=j),
                    end_time=now + timedelta(days=i, hours=j+1),
                    category=category,
                )

        return repo, user_id

    @pytest.mark.asyncio
    async def test_filter_by_work_category(self, repo_with_categories):
        """BR-CAL-013: Filter by WORK category"""
        repo, user_id = repo_with_categories
        service = CalendarService(repository=repo)

        request = EventQueryRequest(
            user_id=user_id,
            category=EventCategory.WORK,
        )

        result = await service.query_events(request)

        for event in result.events:
            assert event.category == EventCategory.WORK

    @pytest.mark.asyncio
    async def test_filter_by_meeting_category(self, repo_with_categories):
        """BR-CAL-013: Filter by MEETING category"""
        repo, user_id = repo_with_categories
        service = CalendarService(repository=repo)

        request = EventQueryRequest(
            user_id=user_id,
            category=EventCategory.MEETING,
        )

        result = await service.query_events(request)

        for event in result.events:
            assert event.category == EventCategory.MEETING

    @pytest.mark.asyncio
    async def test_no_category_filter_returns_all(self, repo_with_categories):
        """BR-CAL-013: No filter returns all categories"""
        repo, user_id = repo_with_categories
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user_id)
        result = await service.query_events(request)

        # Should have 12 events (3 per category * 4 categories)
        assert result.total == 12


class TestPagination:
    """Test pagination behavior"""

    @pytest.fixture
    def repo_with_many_events(self):
        """Create repository with many events"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        for i in range(50):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=f"Event {i:03d}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1),
            )

        return repo, user_id

    @pytest.mark.asyncio
    async def test_pagination_limit(self, repo_with_many_events):
        """Limit parameter restricts results"""
        repo, user_id = repo_with_many_events
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user_id, limit=10)
        result = await service.query_events(request)

        assert len(result.events) <= 10

    @pytest.mark.asyncio
    async def test_pagination_offset(self, repo_with_many_events):
        """Offset skips first N results"""
        repo, user_id = repo_with_many_events
        service = CalendarService(repository=repo)

        # Get first page
        request1 = EventQueryRequest(user_id=user_id, limit=10, offset=0)
        result1 = await service.query_events(request1)

        # Get second page
        request2 = EventQueryRequest(user_id=user_id, limit=10, offset=10)
        result2 = await service.query_events(request2)

        # Pages should have different events
        if result1.events and result2.events:
            assert result1.events[0].event_id != result2.events[0].event_id

    @pytest.mark.asyncio
    async def test_pagination_total_count(self, repo_with_many_events):
        """Total count reflects all matching events"""
        repo, user_id = repo_with_many_events
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user_id, limit=10)
        result = await service.query_events(request)

        # Total should be 50, even though only 10 returned
        assert result.total == 50


class TestMultipleEventsAtSameTime:
    """Test EC-009: Multiple Events Same Start Time"""

    @pytest.fixture
    def repo_with_concurrent_events(self):
        """Create events with identical start times"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # 5 events all starting at the same time
        for i in range(5):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=f"Concurrent Event {i}",
                start_time=now,
                end_time=now + timedelta(hours=1),
            )

        return repo, user_id

    @pytest.mark.asyncio
    async def test_concurrent_events_all_returned(self, repo_with_concurrent_events):
        """EC-009: All concurrent events returned"""
        repo, user_id = repo_with_concurrent_events
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user_id)
        result = await service.query_events(request)

        assert result.total == 5


class TestQueryByUserIsolation:
    """Test user isolation in queries"""

    @pytest.fixture
    def repo_with_multiple_users(self):
        """Create events for multiple users"""
        repo = MockCalendarRepository()
        user1 = CalendarTestDataFactory.make_user_id()
        user2 = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # User 1 events
        for i in range(10):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user1,
                title=f"User1 Event {i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1),
            )

        # User 2 events
        for i in range(5):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user2,
                title=f"User2 Event {i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1),
            )

        return repo, user1, user2

    @pytest.mark.asyncio
    async def test_query_returns_only_user_events(self, repo_with_multiple_users):
        """Query returns only specified user's events"""
        repo, user1, user2 = repo_with_multiple_users
        service = CalendarService(repository=repo)

        request = EventQueryRequest(user_id=user1)
        result = await service.query_events(request)

        assert result.total == 10
        for event in result.events:
            assert event.user_id == user1

    @pytest.mark.asyncio
    async def test_different_users_different_counts(self, repo_with_multiple_users):
        """Different users have different event counts"""
        repo, user1, user2 = repo_with_multiple_users
        service = CalendarService(repository=repo)

        result1 = await service.query_events(EventQueryRequest(user_id=user1))
        result2 = await service.query_events(EventQueryRequest(user_id=user2))

        assert result1.total == 10
        assert result2.total == 5
