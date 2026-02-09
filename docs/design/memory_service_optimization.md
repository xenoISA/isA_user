---
  Google Titans + MIRAS vs. Your Memory Service: Comprehensive Analysis

  Executive Summary

  Google's Titans + MIRAS is a revolutionary AI architecture for real-time, in-model memory that learns during inference. Your Memory Service is an application-level cognitive memory system for persistent user context. They solve different problems but share conceptual overlaps from which you can learn.

  ---
  1. Architectural Comparison

  | Aspect           | Google Titans + MIRAS                  | Your Memory Service                                                |
  |------------------|----------------------------------------|--------------------------------------------------------------------|
  | Level            | Neural architecture (model weights)    | Application service (external storage)                             |
  | Memory Location  | Inside model parameters (MLP)          | PostgreSQL + Qdrant (external)                                     |
  | Update Mechanism | Gradient-based at test-time            | API calls + event-driven                                           |
  | Context Window   | 2M+ tokens in single pass              | Session-based, unlimited via retrieval                             |
  | Memory Structure | 3 layers: contextual, core, persistent | 6 types: factual, episodic, procedural, semantic, working, session |
  | Forgetting       | Adaptive weight decay                  | TTL-based (working) + importance decay (future)                    |

  ---
  2. Key Innovations from Titans You Can Learn From

  2.1 Surprise-Based Memory Storage

  Titans' Approach:
  When surprise is LOW  → Skip permanent storage (routine information)
  When surprise is HIGH → Prioritize permanent storage (anomalous/important)

  Your Current Implementation:
  - Uses importance_score (0.0-1.0) as static input
  - No dynamic detection of "surprising" vs "routine" information

  Optimization Opportunity:
  # Add a "novelty detection" layer to your extraction
  class NoveltyDetector:
      async def calculate_surprise_score(
          self, 
          user_id: str, 
          new_content: str,
          existing_memories: List[Dict]
      ) -> float:
          """
          Calculate how 'surprising' new information is relative to existing memory.
          Uses embedding similarity to detect novelty.
          """
          # 1. Generate embedding for new content
          new_embedding = await self.generate_embedding(new_content)

          # 2. Compare against existing memory embeddings in Qdrant
          similar_memories = await self.qdrant.search(
              collection="memory_factual",
              query_vector=new_embedding,
              limit=10
          )

          # 3. Calculate surprise (inverse of max similarity)
          if not similar_memories:
              return 1.0  # Completely novel

          max_similarity = max(m.score for m in similar_memories)
          surprise_score = 1.0 - max_similarity  # High surprise = low similarity

          return surprise_score

  Impact: Automatically prioritize storing truly new information while avoiding redundant memories.

  ---
  2.2 Momentum-Based Context Tracking

  Titans' Approach:
  - Uses momentum to capture relevant surrounding context even when individual tokens aren't surprising
  - Maintains temporal coherence across sequences

  Your Current Implementation:
  - Session memory tracks interaction_sequence
  - No concept of "momentum" for related information capture

  Optimization Opportunity:
  # In session_service.py - add momentum-aware context
  class MomentumContextTracker:
      def __init__(self, decay_factor: float = 0.9):
          self.decay_factor = decay_factor
          self.momentum_scores = {}  # session_id -> running momentum

      async def update_momentum(
          self,
          session_id: str,
          current_importance: float,
          topic_continuity: float  # 0-1, how related to previous messages
      ):
          """
          Momentum = α * current + (1-α) * previous
          High momentum means we're in an important conversation thread
          """
          prev_momentum = self.momentum_scores.get(session_id, 0.5)
          new_momentum = (
              self.decay_factor * topic_continuity * current_importance +
              (1 - self.decay_factor) * prev_momentum
          )
          self.momentum_scores[session_id] = new_momentum

          # If momentum is high, boost importance scores for all memories in this thread
          return new_momentum

  ---
  2.3 Adaptive Weight Decay (Intelligent Forgetting)

  Titans' Approach:
  - Forgetting gate manages finite memory capacity
  - Recent/important information preserved, old/irrelevant decayed

  Your Current Implementation:
  - Working memory: TTL-based expiration (static)
  - Other memories: No decay mechanism (accumulate forever)

  Optimization Opportunity - Add Memory Decay Algorithm:

  # New file: memory_decay_service.py
  class MemoryDecayService:
      """
      Implements Titans-inspired adaptive forgetting
      """

      async def calculate_decay(
          self,
          memory: Dict,
          current_time: datetime
      ) -> float:
          """
          Decay formula inspired by Ebbinghaus + Titans adaptive weight decay
          """
          # Factors that REDUCE decay (preserve memory)
          importance = memory.get('importance_score', 0.5)
          access_frequency = memory.get('access_count', 0) / max(1, days_since_creation)
          recency = 1.0 / (1 + days_since_last_access)

          # Titans-style: memories accessed during "high momentum" periods decay slower
          momentum_boost = memory.get('momentum_at_creation', 0.5)

          # Composite retention score
          retention = (
              0.3 * importance +
              0.2 * access_frequency +
              0.3 * recency +
              0.2 * momentum_boost
          )

          # Decay = 1 - retention (memories with low retention should be forgotten)
          return 1.0 - retention

      async def run_decay_cycle(self, user_id: str):
          """
          Periodic job to decay/archive low-retention memories
          """
          for memory_type in MemoryType:
              memories = await self.list_memories(user_id, memory_type)

              for memory in memories:
                  decay_score = await self.calculate_decay(memory)

                  if decay_score > 0.9:  # Very decayed
                      await self.archive_memory(memory)  # Move to cold storage
                  elif decay_score > 0.7:
                      # Reduce importance score (soft decay)
                      await self.reduce_importance(memory, factor=0.9)

  ---
  2.4 Multi-Layer Memory Architecture

  Titans' Approach:
  - Contextual Memory: Short-term attention (current context)
  - Core Memory: In-context learning (session-level)
  - Persistent Memory: Fixed weights (long-term knowledge)

  Your Current Implementation:
  - 6 memory types by cognitive function
  - No hierarchical access speed/importance

  Optimization Opportunity - Add Memory Tiers:

  ┌─────────────────────────────────────────────────────────────┐
  │                    MEMORY TIERS (Titans-Inspired)           │
  ├─────────────────────────────────────────────────────────────┤
  │  Tier 1: HOT MEMORY (Redis Cache)                           │
  │  - Working memory                                           │
  │  - Recent session context (last 10 messages)                │
  │  - High-access factual memories                             │
  │  - Latency: <10ms                                           │
  ├─────────────────────────────────────────────────────────────┤
  │  Tier 2: WARM MEMORY (PostgreSQL + Qdrant)                  │
  │  - Active session histories                                 │
  │  - Frequently accessed facts/episodes                       │
  │  - Recent procedural memories                               │
  │  - Latency: <100ms                                          │
  ├─────────────────────────────────────────────────────────────┤
  │  Tier 3: COLD MEMORY (Archive Storage)                      │
  │  - Old sessions (compressed summaries)                      │
  │  - Rarely accessed memories                                 │
  │  - Decayed but potentially relevant memories                │
  │  - Latency: <500ms (on-demand retrieval)                    │
  └─────────────────────────────────────────────────────────────┘

  ---
  3. MIRAS Framework Components → Your Design Mapping

  | MIRAS Component     | Your Equivalent                        | Enhancement Opportunity                        |
  |---------------------|----------------------------------------|------------------------------------------------|
  | Memory Architecture | PostgreSQL tables + Qdrant collections | Add tiered storage (hot/warm/cold)             |
  | Attentional Bias    | importance_score field                 | Add dynamic surprise-based scoring             |
  | Retention Gate      | Working memory TTL                     | Extend to all memory types with adaptive decay |
  | Memory Algorithm    | LLM extraction + embeddings            | Add online learning for extraction improvement |

  ---
  4. Specific Recommendations for Your Memory Service

  4.1 Immediate Wins (Low Effort, High Impact)

  A. Add Surprise Detection to Extraction Pipeline

  # In factual_service.py store_factual_memory()
  async def store_factual_memory(self, user_id, dialog_content, importance_score):
      # NEW: Calculate surprise before storage
      surprise = await self.novelty_detector.calculate_surprise(
          user_id,
          dialog_content
      )

      # Adjust importance based on surprise (Titans-style)
      adjusted_importance = min(1.0, importance_score * (0.5 + 0.5 * surprise))

      # Skip storage if both importance AND surprise are low
      if adjusted_importance < 0.2 and surprise < 0.3:
          logger.info(f"Skipping low-novelty memory: surprise={surprise}")
          return MemoryOperationResult(
              success=True,
              operation="skip_redundant",
              message="Information already known, skipped storage"
          )

      # Continue with normal extraction...

  B. Implement Memory Consolidation (Compression)

  # Titans consolidates information - you should too
  async def consolidate_session_memories(self, user_id: str, session_id: str):
      """
      When session ends, consolidate into summary + extract key memories
      """
      session_memories = await self.get_session_memories(user_id, session_id)

      # Use LLM to summarize entire session
      summary = await self.llm_summarize(session_memories)

      # Extract key facts/episodes to promote to long-term memory
      extracted = await self.extract_key_memories(session_memories)

      # Store summary, archive raw session data
      await self.store_session_summary(session_id, summary)
      await self.archive_session_raw(session_id)  # Move to cold storage

      # Promote important extractions to permanent memory
      for memory in extracted:
          if memory['type'] == 'factual':
              await self.store_factual_memory(...)

  4.2 Medium-Term Enhancements

  A. Real-Time Importance Adjustment

  # Track which memories get accessed and boost their importance
  async def on_memory_access(self, memory_id: str, memory_type: str, user_id: str):
      # Increment access count (you already do this)
      await repo.increment_access_count(memory_id, user_id)

      # NEW: Boost importance for frequently accessed memories
      memory = await repo.get_by_id(memory_id, user_id)
      if memory['access_count'] > 10:
          new_importance = min(1.0, memory['importance_score'] * 1.1)
          await repo.update(memory_id, {'importance_score': new_importance}, user_id)

  B. Add Cross-Memory Association Graph

  # Titans maintains relationships; you have related_facts but can expand
  async def build_memory_associations(self, user_id: str, new_memory: Dict):
      """
      When storing new memory, find and link related memories across types
      """
      embedding = await self.get_embedding(new_memory['content'])

      # Search all memory types for related content
      associations = []
      for memory_type in MemoryType:
          related = await self.qdrant_search(
              collection=f"memory_{memory_type.value}",
              vector=embedding,
              filter={"user_id": user_id},
              limit=5,
              score_threshold=0.7
          )
          associations.extend(related)

      # Store bidirectional associations
      await self.store_associations(new_memory['id'], associations)

  4.3 Long-Term Architecture Evolution

  A. Add "Test-Time Learning" for Extraction Models

  Titans updates its weights at inference time. You can approximate this:

  class AdaptiveExtractor:
      """
      Track extraction quality and adapt prompts/parameters
      """

      async def learn_from_feedback(
          self,
          extraction_id: str,
          user_feedback: str,  # "good", "bad", "partial"
          corrections: Optional[Dict] = None
      ):
          # Store feedback for this extraction pattern
          await self.store_feedback(extraction_id, user_feedback, corrections)

          # If we accumulate enough negative feedback for a pattern
          # Adjust extraction prompt or add to fine-tuning queue
          if await self.should_adapt_prompt(pattern_type):
              await self.update_extraction_prompt(pattern_type)

  B. Implement Hierarchical Memory Attention

  # When retrieving context, use Titans-style attention weighting
  async def get_weighted_context(
      self,
      user_id: str,
      query: str,
      max_tokens: int = 2000
  ) -> List[Dict]:
      """
      Returns memories weighted by:
      1. Semantic relevance (embedding similarity)
      2. Recency (temporal attention)
      3. Importance (surprise at creation time)
      4. Access frequency (proven usefulness)
      """
      candidates = await self.search_all_memories(user_id, query, limit=50)

      for memory in candidates:
          memory['attention_score'] = (
              0.4 * memory['similarity_score'] +
              0.2 * self.recency_score(memory) +
              0.2 * memory['importance_score'] +
              0.2 * self.frequency_score(memory)
          )

      # Sort by attention and fit within token budget
      candidates.sort(key=lambda x: x['attention_score'], reverse=True)
      return self.fit_to_token_budget(candidates, max_tokens)

  ---
  5. Summary: Key Takeaways

  | Titans Innovation   | Your Action Item                     | Priority        |
  |---------------------|--------------------------------------|-----------------|
  | Surprise Metric     | Add novelty detection before storage | 🔴 High         |
  | Momentum            | Track conversation thread importance | 🟡 Medium       |
  | Adaptive Forgetting | Implement decay for all memory types | 🔴 High         |
  | Multi-Layer Memory  | Add Redis hot cache tier             | 🟡 Medium       |
  | Test-Time Learning  | Feedback loop for extraction quality | 🟢 Low (future) |
  | 2M+ Token Context   | Memory consolidation + summarization | 🔴 High         |

  ---
  6. Recommended Implementation Order

  1. Phase 1: Surprise-Based Storage (1-2 weeks)
    - Add NoveltyDetector class
    - Integrate with extraction endpoints
    - Skip redundant memories automatically
  2. Phase 2: Memory Decay System (2-3 weeks)
    - Add decay_score to all memory types
    - Implement background decay job
    - Add cold storage tier
  3. Phase 3: Session Consolidation (1-2 weeks)
    - Auto-summarize ended sessions
    - Promote key facts to long-term memory
    - Archive raw session data
  4. Phase 4: Tiered Storage (3-4 weeks)
    - Add Redis for hot memory
    - Implement attention-weighted retrieval
    - Add memory association graph

  ---
  Sources:
  - https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/
  - https://www.marktechpost.com/2025/12/07/from-transformers-to-associative-memory-how-titans-and-miras-rethink-long-context-modeling/
  - https://www.etavrian.com/news/google-titans-miras-long-context-memory
  - https://meterpreter.org/google-titans-miras-new-architecture-for-2m-token-long-term-ai-memory/