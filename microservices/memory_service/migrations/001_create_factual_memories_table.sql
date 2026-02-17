-- Memory Service Migration: Create factual_memories table
-- Version: 001
-- Date: 2025-01-24
-- Note: No embedding field - vectors stored in Qdrant

-- ====================
-- Factual Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.factual_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'factual',

    -- Content (no embedding - stored in Qdrant)
    content TEXT NOT NULL,

    -- Fact structure (subject-predicate-object)
    fact_type VARCHAR(100) NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_value TEXT NOT NULL,

    -- Factual memory specific
    fact_context TEXT,
    source VARCHAR(255),
    verification_status VARCHAR(50) DEFAULT 'unverified',
    related_facts JSONB DEFAULT '[]'::jsonb,

    -- Cognitive attributes
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
    confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes for factual memories
CREATE INDEX idx_factual_memories_user_id ON memory.factual_memories(user_id);
CREATE INDEX idx_factual_memories_fact_type ON memory.factual_memories(fact_type);
CREATE INDEX idx_factual_memories_subject ON memory.factual_memories USING gin(to_tsvector('english', subject));
CREATE INDEX idx_factual_memories_predicate ON memory.factual_memories(predicate);
CREATE INDEX idx_factual_memories_confidence ON memory.factual_memories(confidence);
CREATE INDEX idx_factual_memories_verification ON memory.factual_memories(verification_status);
CREATE INDEX idx_factual_memories_created_at ON memory.factual_memories(created_at DESC);
CREATE INDEX idx_factual_memories_importance ON memory.factual_memories(importance_score DESC);

-- Unique constraint for duplicate detection
CREATE UNIQUE INDEX idx_factual_memories_unique_fact ON memory.factual_memories(user_id, subject, predicate);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_factual_memories_updated_at
    BEFORE UPDATE ON memory.factual_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- Comments
COMMENT ON TABLE memory.factual_memories IS 'Factual memories - facts and declarative knowledge in subject-predicate-object format';
COMMENT ON COLUMN memory.factual_memories.id IS 'Memory ID - also used as Qdrant point ID for vector storage';
COMMENT ON COLUMN memory.factual_memories.fact_type IS 'Type of fact: person, place, event, preference, skill, etc.';
