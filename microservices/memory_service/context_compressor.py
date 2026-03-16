"""
Context Compressor — SimpleMem-inspired aggressive context compression

Compresses retrieved memories into focused, reasoning-aligned summaries
before injection into prompts. Targets 5-10x token reduction by using
an LLM to distill the most relevant information for the query.

Usage:
    from microservices.memory_service.context_compressor import ContextCompressor, compress_memories

    compressor = ContextCompressor()
    compressed = await compressor.compress_memories(memories, target_tokens=500, query_context="...")

    # Or use the module-level convenience function:
    compressed = await compress_memories(memories, target_tokens=500, query_context="...")
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

from isa_model.inference_client import AsyncISAModel

logger = logging.getLogger(__name__)

# Default compression prompt template (from issue spec)
COMPRESSION_PROMPT_TEMPLATE = """\
You are a memory compression expert. Given the user's query and retrieved memories, produce a focused summary that:
1. Preserves facts directly relevant to the query
2. Removes redundant information
3. Maintains temporal ordering of events
4. Keeps key entities and relationships
5. Targets approximately {target_tokens} tokens

Query context: {query_context}

Retrieved memories:
{formatted_memories}

Compressed summary:"""


class ContextCompressor:
    """
    Compresses retrieved memories into concise, query-relevant summaries.

    Uses an LLM to intelligently compress multiple memory results into a
    single focused summary. Falls back to simple concatenation if the LLM
    is unavailable.
    """

    def __init__(
        self,
        model_url: Optional[str] = None,
        default_target_tokens: int = 500,
        model_name: str = "gpt-4o-mini",
    ):
        """
        Args:
            model_url: ISA Model service URL. Defaults to ISA_MODEL_URL env var or localhost:8082.
            default_target_tokens: Default target token count for compression.
            model_name: Model to use for compression calls.
        """
        self.model_url = model_url or os.getenv("ISA_MODEL_URL", "http://localhost:8082")
        self.default_target_tokens = default_target_tokens
        self.model_name = model_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compress_memories(
        self,
        memories: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
        target_tokens: Optional[int] = None,
        query_context: str = "",
    ) -> str:
        """
        Compress retrieved memories into a focused summary.

        Args:
            memories: Either a dict of {memory_type: [memory_dicts]} (grouped search results)
                      or a flat list of memory dicts.
            target_tokens: Approximate target token count for the summary.
                           Uses default_target_tokens if not provided.
            query_context: The user's query to guide what information to prioritize.

        Returns:
            Compressed summary string. Empty string if no memories.
        """
        if target_tokens is None:
            target_tokens = self.default_target_tokens

        # Format memories for the prompt
        formatted = self._format_memories_for_prompt(memories)
        if not formatted.strip():
            return ""

        # Build the compression prompt
        prompt = self._build_compression_prompt(formatted, query_context, target_tokens)

        # Attempt LLM compression
        try:
            compressed = await self._call_llm(prompt)
            if compressed:
                logger.info(
                    f"Compressed memories to ~{len(compressed.split())} words "
                    f"(target: {target_tokens} tokens)"
                )
                return compressed
        except Exception as e:
            logger.warning(f"LLM compression failed, falling back to concatenation: {e}")

        # Fallback: return concatenated memory contents
        return self._fallback_concatenate(memories)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_memories_for_prompt(
        self,
        memories: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    ) -> str:
        """
        Format memories into a string suitable for the compression prompt.

        Handles both grouped (dict) and flat (list) memory formats.
        """
        if isinstance(memories, list):
            return self._format_flat_list(memories)
        return self._format_grouped_dict(memories)

    def _format_grouped_dict(self, memories: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format grouped {type: [memories]} dict"""
        sections = []
        for memory_type, items in memories.items():
            if not items:
                continue
            header = f"[{memory_type.upper()}]"
            entries = []
            for item in items:
                content = item.get("content", "")
                score = item.get("similarity_score")
                if score is not None:
                    entries.append(f"- (score: {score:.2f}) {content}")
                else:
                    entries.append(f"- {content}")
            sections.append(f"{header}\n" + "\n".join(entries))
        return "\n\n".join(sections)

    def _format_flat_list(self, memories: List[Dict[str, Any]]) -> str:
        """Format a flat list of memory dicts"""
        lines = []
        for item in memories:
            content = item.get("content", "")
            mem_type = item.get("memory_type", "unknown")
            score = item.get("similarity_score")
            if score is not None:
                lines.append(f"- [{mem_type}] (score: {score:.2f}) {content}")
            else:
                lines.append(f"- [{mem_type}] {content}")
        return "\n".join(lines)

    def _build_compression_prompt(
        self,
        formatted_memories: str,
        query_context: str,
        target_tokens: int,
    ) -> str:
        """Build the LLM compression prompt from template"""
        return COMPRESSION_PROMPT_TEMPLATE.format(
            target_tokens=target_tokens,
            query_context=query_context,
            formatted_memories=formatted_memories,
        )

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_concatenate(
        self,
        memories: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    ) -> str:
        """
        Simple concatenation fallback when LLM is unavailable.

        Returns all memory contents joined by newlines.
        """
        contents: List[str] = []

        if isinstance(memories, list):
            for item in memories:
                c = item.get("content", "").strip()
                if c:
                    contents.append(c)
        else:
            for items in memories.values():
                for item in items:
                    c = item.get("content", "").strip()
                    if c:
                        contents.append(c)

        return "\n".join(contents)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """
        Call the ISA Model service to compress memories.

        Uses the same AsyncISAModel client pattern as session_service.py.
        """
        async with AsyncISAModel(base_url=self.model_url) as client:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a memory compression expert. Produce concise, information-dense summaries."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

async def compress_memories(
    memories: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    target_tokens: int = 500,
    query_context: str = "",
    model_url: Optional[str] = None,
) -> str:
    """
    Convenience function to compress memories without instantiating a class.

    Args:
        memories: Grouped or flat memory results.
        target_tokens: Approximate target token count.
        query_context: User's query for relevance guidance.
        model_url: Optional ISA Model URL override.

    Returns:
        Compressed summary string.
    """
    compressor = ContextCompressor(model_url=model_url)
    return await compressor.compress_memories(
        memories=memories,
        target_tokens=target_tokens,
        query_context=query_context,
    )
