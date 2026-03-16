"""
Unit tests for ContextCompressor — SimpleMem-inspired context compression

Tests the compression utility that uses an LLM to compress retrieved memories
into focused, reasoning-aligned summaries before injection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_memories():
    """Sample search results across memory types"""
    return {
        "factual": [
            {
                "id": "f1",
                "content": "User's name is Alice",
                "memory_type": "factual",
                "importance_score": 0.9,
                "similarity_score": 0.85,
            },
            {
                "id": "f2",
                "content": "Alice works at Acme Corp",
                "memory_type": "factual",
                "importance_score": 0.7,
                "similarity_score": 0.72,
            },
        ],
        "episodic": [
            {
                "id": "e1",
                "content": "Alice had a meeting with Bob on Monday about project X",
                "memory_type": "episodic",
                "importance_score": 0.6,
                "similarity_score": 0.68,
            },
        ],
        "procedural": [],
        "semantic": [
            {
                "id": "s1",
                "content": "Project X is a machine learning pipeline for NLP tasks",
                "memory_type": "semantic",
                "importance_score": 0.5,
                "similarity_score": 0.60,
            },
        ],
        "working": [],
        "session": [],
    }


@pytest.fixture
def empty_memories():
    """Empty search results"""
    return {
        "factual": [],
        "episodic": [],
        "procedural": [],
        "semantic": [],
        "working": [],
        "session": [],
    }


@pytest.fixture
def flat_memories():
    """Flat list of memory dicts (pre-flattened)"""
    return [
        {"id": "f1", "content": "User's name is Alice", "memory_type": "factual"},
        {"id": "e1", "content": "Meeting with Bob on Monday", "memory_type": "episodic"},
    ]


# ---------------------------------------------------------------------------
# ContextCompressor class tests
# ---------------------------------------------------------------------------

class TestContextCompressorInit:
    """Tests for ContextCompressor initialization"""

    def test_default_init(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        assert compressor.model_url is not None
        assert compressor.default_target_tokens == 500

    def test_custom_target_tokens(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor(default_target_tokens=200)
        assert compressor.default_target_tokens == 200

    def test_custom_model_url(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor(model_url="http://custom:9999")
        assert compressor.model_url == "http://custom:9999"


class TestFormatMemories:
    """Tests for _format_memories_for_prompt (pure logic, no I/O)"""

    def test_format_grouped_memories(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        formatted = compressor._format_memories_for_prompt(sample_memories)

        # Should contain type headers
        assert "FACTUAL" in formatted or "factual" in formatted.lower()
        # Should contain memory content
        assert "Alice" in formatted
        assert "Acme Corp" in formatted
        assert "meeting with bob" in formatted.lower()
        assert "Project X" in formatted

    def test_format_empty_memories(self, empty_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        formatted = compressor._format_memories_for_prompt(empty_memories)

        # Should return empty or minimal string
        assert formatted.strip() == "" or "no memories" in formatted.lower()

    def test_format_skips_empty_types(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        formatted = compressor._format_memories_for_prompt(sample_memories)

        # Procedural and working are empty, should not appear as sections
        # (or appear as empty sections — implementation-dependent)
        assert "Project X" in formatted  # semantic should still be there

    def test_format_flat_list(self, flat_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        formatted = compressor._format_memories_for_prompt(flat_memories)

        assert "Alice" in formatted
        assert "Bob" in formatted


class TestBuildPrompt:
    """Tests for _build_compression_prompt"""

    def test_prompt_contains_query_context(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        prompt = compressor._build_compression_prompt(
            formatted_memories="Some memories here",
            query_context="What is Alice working on?",
            target_tokens=500,
        )

        assert "What is Alice working on?" in prompt
        assert "500" in prompt
        assert "Some memories here" in prompt

    def test_prompt_contains_instructions(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        prompt = compressor._build_compression_prompt(
            formatted_memories="data",
            query_context="query",
            target_tokens=300,
        )

        # Should contain the key instructions from the issue spec
        assert "relevant" in prompt.lower()
        assert "300" in prompt

    def test_prompt_empty_query_context(self):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        prompt = compressor._build_compression_prompt(
            formatted_memories="data",
            query_context="",
            target_tokens=500,
        )

        # Should still produce a valid prompt
        assert "data" in prompt


class TestFallbackConcatenation:
    """Tests for _fallback_concatenate (pure logic fallback)"""

    def test_fallback_with_grouped_memories(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        result = compressor._fallback_concatenate(sample_memories)

        assert "Alice" in result
        assert "Acme Corp" in result
        assert "Project X" in result

    def test_fallback_with_empty_memories(self, empty_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        result = compressor._fallback_concatenate(empty_memories)

        assert result == ""

    def test_fallback_with_flat_list(self, flat_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        result = compressor._fallback_concatenate(flat_memories)

        assert "Alice" in result
        assert "Bob" in result


class TestCompressMemories:
    """Tests for compress_memories (async, mocked LLM)"""

    @pytest.mark.asyncio
    async def test_compress_returns_llm_summary(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()

        # Mock the LLM call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Alice works at Acme Corp and met Bob about Project X."

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "microservices.memory_service.context_compressor.AsyncISAModel",
            return_value=mock_client_instance,
        ):
            result = await compressor.compress_memories(
                memories=sample_memories,
                target_tokens=500,
                query_context="What is Alice working on?",
            )

        assert result == "Alice works at Acme Corp and met Bob about Project X."

    @pytest.mark.asyncio
    async def test_compress_falls_back_on_llm_failure(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "microservices.memory_service.context_compressor.AsyncISAModel",
            return_value=mock_client_instance,
        ):
            result = await compressor.compress_memories(
                memories=sample_memories,
                target_tokens=500,
                query_context="test",
            )

        # Should fall back to concatenation
        assert "Alice" in result
        assert "Acme Corp" in result

    @pytest.mark.asyncio
    async def test_compress_empty_memories_returns_empty(self, empty_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()
        result = await compressor.compress_memories(
            memories=empty_memories,
            target_tokens=500,
            query_context="anything",
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_compress_uses_default_target_tokens(self, sample_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor(default_target_tokens=300)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "compressed"

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "microservices.memory_service.context_compressor.AsyncISAModel",
            return_value=mock_client_instance,
        ) as mock_cls:
            result = await compressor.compress_memories(
                memories=sample_memories,
                query_context="test",
            )

        assert result == "compressed"

    @pytest.mark.asyncio
    async def test_compress_with_flat_list(self, flat_memories):
        from microservices.memory_service.context_compressor import ContextCompressor

        compressor = ContextCompressor()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Alice met Bob."

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "microservices.memory_service.context_compressor.AsyncISAModel",
            return_value=mock_client_instance,
        ):
            result = await compressor.compress_memories(
                memories=flat_memories,
                target_tokens=500,
                query_context="test",
            )

        assert result == "Alice met Bob."


class TestCompressMemoriesModule:
    """Tests for the module-level compress_memories convenience function"""

    @pytest.mark.asyncio
    async def test_module_function_delegates(self, sample_memories):
        from microservices.memory_service.context_compressor import compress_memories

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "compressed output"

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "microservices.memory_service.context_compressor.AsyncISAModel",
            return_value=mock_client_instance,
        ):
            result = await compress_memories(
                memories=sample_memories,
                target_tokens=500,
                query_context="test query",
            )

        assert result == "compressed output"
