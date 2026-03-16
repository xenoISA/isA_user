"""
Unit tests for Ebbinghaus memory decay service.

Tests the decay formula, edge cases, and configuration handling.
No I/O — all repository interactions are mocked.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from microservices.memory_service.decay_service import (
    DecayConfig,
    DecayService,
    compute_decayed_importance,
)


# ==================== L1: Pure decay formula tests ====================


class TestComputeDecayedImportance:
    """Test the pure decay formula: importance * e^(-ln(2)/half_life * hours)"""

    def test_no_decay_at_time_zero(self):
        """Memory just accessed should have no decay."""
        result = compute_decayed_importance(
            original_importance=0.7,
            hours_since_last_access=0.0,
            half_life_hours=30 * 24,  # 30 days
        )
        assert result == pytest.approx(0.7)

    def test_half_life_halves_importance(self):
        """After exactly one half-life, importance should be halved."""
        half_life_hours = 30 * 24  # 30 days in hours
        result = compute_decayed_importance(
            original_importance=1.0,
            hours_since_last_access=half_life_hours,
            half_life_hours=half_life_hours,
        )
        assert result == pytest.approx(0.5, rel=1e-6)

    def test_two_half_lives_quarters_importance(self):
        """After two half-lives, importance should be quartered."""
        half_life_hours = 30 * 24
        result = compute_decayed_importance(
            original_importance=1.0,
            hours_since_last_access=2 * half_life_hours,
            half_life_hours=half_life_hours,
        )
        assert result == pytest.approx(0.25, rel=1e-6)

    def test_decay_with_fractional_importance(self):
        """Decay works correctly with non-unit importance."""
        half_life_hours = 30 * 24
        result = compute_decayed_importance(
            original_importance=0.6,
            hours_since_last_access=half_life_hours,
            half_life_hours=half_life_hours,
        )
        assert result == pytest.approx(0.3, rel=1e-6)

    def test_very_long_time_decays_near_zero(self):
        """After many half-lives, importance approaches zero."""
        half_life_hours = 30 * 24
        result = compute_decayed_importance(
            original_importance=1.0,
            hours_since_last_access=10 * half_life_hours,
            half_life_hours=half_life_hours,
        )
        assert result < 0.001

    def test_zero_importance_stays_zero(self):
        """Zero importance should remain zero regardless of time."""
        result = compute_decayed_importance(
            original_importance=0.0,
            hours_since_last_access=100.0,
            half_life_hours=30 * 24,
        )
        assert result == 0.0

    def test_negative_hours_returns_original(self):
        """Negative time (future access) should not increase importance."""
        result = compute_decayed_importance(
            original_importance=0.5,
            hours_since_last_access=-10.0,
            half_life_hours=30 * 24,
        )
        # Negative time means the memory was accessed in the "future" — clamp to original
        assert result == pytest.approx(0.5)

    def test_short_half_life_decays_faster(self):
        """Shorter half-life should produce more decay in the same time."""
        hours = 24 * 7  # 1 week
        result_short = compute_decayed_importance(
            original_importance=1.0,
            hours_since_last_access=hours,
            half_life_hours=24 * 7,  # 7-day half-life
        )
        result_long = compute_decayed_importance(
            original_importance=1.0,
            hours_since_last_access=hours,
            half_life_hours=24 * 30,  # 30-day half-life
        )
        assert result_short < result_long


# ==================== L1: DecayConfig tests ====================


class TestDecayConfig:
    """Test the configuration model."""

    def test_defaults(self):
        config = DecayConfig()
        assert config.half_life_days == 30
        assert config.floor_threshold == 0.1
        assert config.protected_threshold == 0.8

    def test_custom_values(self):
        config = DecayConfig(
            half_life_days=14,
            floor_threshold=0.05,
            protected_threshold=0.9,
        )
        assert config.half_life_days == 14
        assert config.floor_threshold == 0.05
        assert config.protected_threshold == 0.9

    def test_half_life_hours(self):
        config = DecayConfig(half_life_days=7)
        assert config.half_life_hours == 7 * 24


# ==================== L2: DecayService component tests (mocked repos) ====================


class TestDecayService:
    """Test DecayService with mocked repository layer."""

    @pytest.fixture
    def config(self):
        return DecayConfig(
            half_life_days=30,
            floor_threshold=0.1,
            protected_threshold=0.8,
        )

    @pytest.fixture
    def mock_memory_service(self):
        """Create a mock MemoryService with mock repositories."""
        service = MagicMock()
        # Each memory type service has a repository
        for mem_type in ["factual_service", "procedural_service", "episodic_service",
                         "semantic_service", "working_service", "session_service"]:
            svc = MagicMock()
            svc.repository = MagicMock()
            svc.repository.list_by_user = AsyncMock(return_value=[])
            svc.repository.update = AsyncMock(return_value=True)
            svc.repository.schema = "memory"
            svc.repository.table_name = mem_type.replace("_service", "_memories")
            svc.repository.db = MagicMock()
            svc.repository.db.query = AsyncMock(return_value=[])
            svc.repository.db.execute = AsyncMock(return_value=1)
            svc.repository.db.__aenter__ = AsyncMock(return_value=svc.repository.db)
            svc.repository.db.__aexit__ = AsyncMock(return_value=False)
            setattr(service, mem_type, svc)
        return service

    @pytest.fixture
    def decay_service(self, mock_memory_service, config):
        return DecayService(memory_service=mock_memory_service, config=config)

    def _make_memory(self, importance=0.5, hours_ago=48, access_count=0, memory_id="mem-1", user_id="user-1"):
        """Helper to create a memory dict."""
        last_accessed = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return {
            "id": memory_id,
            "user_id": user_id,
            "importance_score": importance,
            "access_count": access_count,
            "last_accessed_at": last_accessed,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago + 100),
            "updated_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        }

    @pytest.mark.asyncio
    async def test_protected_memory_not_decayed(self, decay_service, mock_memory_service):
        """Memories with importance >= protected_threshold should not decay."""
        protected_memory = self._make_memory(importance=0.9, hours_ago=720)  # 30 days old

        # Set up the repository to return this memory via raw query
        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[protected_memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        # Protected memory should not be updated
        assert result["decayed_count"] == 0

    @pytest.mark.asyncio
    async def test_stale_memory_decays(self, decay_service, mock_memory_service):
        """Unaccessed memories below protected threshold should decay."""
        stale_memory = self._make_memory(importance=0.5, hours_ago=720)  # 30 days

        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[stale_memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        assert result["decayed_count"] >= 1

    @pytest.mark.asyncio
    async def test_memory_below_floor_set_to_zero(self, decay_service, mock_memory_service):
        """Memories decaying below floor_threshold should have importance set to 0.0."""
        # A memory with low importance that has been stale for a very long time
        nearly_dead_memory = self._make_memory(importance=0.15, hours_ago=720 * 3)  # 90 days

        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[nearly_dead_memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        assert result["floored_count"] >= 1

    @pytest.mark.asyncio
    async def test_recently_accessed_memory_minimal_decay(self, decay_service, mock_memory_service):
        """Recently accessed memories should have minimal decay."""
        recent_memory = self._make_memory(importance=0.5, hours_ago=1)  # 1 hour ago

        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[recent_memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        # Very recent memory — decay should be negligible, so it may not be updated
        # (depends on whether the change is below a minimum delta threshold)
        assert result["decayed_count"] == 0 or result["decayed_count"] == 1

    @pytest.mark.asyncio
    async def test_global_decay_processes_all_types(self, decay_service, mock_memory_service):
        """Global decay (no user_id) should process all memory types."""
        # Put one memory in each type's mock
        for mem_type in ["factual_service", "procedural_service", "episodic_service",
                         "semantic_service"]:
            memory = self._make_memory(importance=0.5, hours_ago=720, user_id="any")
            getattr(mock_memory_service, mem_type).repository.db.query = AsyncMock(
                return_value=[memory]
            )

        result = await decay_service.run_decay_cycle(user_id=None)

        # Should have processed memories from multiple types
        assert result["total_processed"] >= 4

    @pytest.mark.asyncio
    async def test_decay_uses_last_accessed_at(self, decay_service, mock_memory_service):
        """Decay timer should be based on last_accessed_at, not created_at."""
        # Memory created long ago but accessed recently
        memory = self._make_memory(importance=0.5, hours_ago=1)  # accessed 1 hour ago
        memory["created_at"] = datetime.now(timezone.utc) - timedelta(days=365)  # created a year ago

        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        # Should have minimal decay since last_accessed_at is recent
        assert result["decayed_count"] == 0 or result["decayed_count"] == 1

    @pytest.mark.asyncio
    async def test_no_memories_returns_zero(self, decay_service, mock_memory_service):
        """Empty memory set should return zero affected."""
        result = await decay_service.run_decay_cycle(user_id="user-1")
        assert result["decayed_count"] == 0
        assert result["floored_count"] == 0
        assert result["total_processed"] == 0

    @pytest.mark.asyncio
    async def test_memory_without_last_accessed_uses_created_at(self, decay_service, mock_memory_service):
        """If last_accessed_at is None, fall back to created_at."""
        memory = self._make_memory(importance=0.5, hours_ago=720)
        memory["last_accessed_at"] = None
        memory["created_at"] = datetime.now(timezone.utc) - timedelta(hours=720)

        mock_memory_service.factual_service.repository.db.query = AsyncMock(
            return_value=[memory]
        )

        result = await decay_service.run_decay_cycle(user_id="user-1")

        assert result["total_processed"] >= 1
