-- Memory Service Migration: Create semantic_memories table
-- Version: 004
-- Date: 2025-01-24

-- ====================
-- Semantic Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.semantic_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'semantic',

    -- Content
    content TEXT NOT NULL,

    -- Concept structure
    concept_type VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,

    -- Semantic memory specific
    abstraction_level VARCHAR(50) DEFAULT 'medium' CHECK (abstraction_level IN ('low', 'medium', 'high')),
    related_concepts TEXT[] DEFAULT '{}',
    category VARCHAR(100) NOT NULL,

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

-- Indexes for semantic memories
CREATE INDEX idx_semantic_memories_user_id ON memory.semantic_memories(user_id);
CREATE INDEX idx_semantic_memories_concept_type ON memory.semantic_memories(concept_type);
CREATE INDEX idx_semantic_memories_category ON memory.semantic_memories(category);
CREATE INDEX idx_semantic_memories_abstraction ON memory.semantic_memories(abstraction_level);
CREATE INDEX idx_semantic_memories_definition ON memory.semantic_memories USING gin(to_tsvector('english', definition));
CREATE INDEX idx_semantic_memories_created_at ON memory.semantic_memories(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_semantic_memories_updated_at
    BEFORE UPDATE ON memory.semantic_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- Comments
COMMENT ON TABLE memory.semantic_memories IS 'Semantic memories - concepts and general knowledge with definitions';
COMMENT ON COLUMN memory.semantic_memories.id IS 'Memory ID - also used as Qdrant point ID';
COMMENT ON COLUMN memory.semantic_memories.properties IS 'Concept properties as JSON object';
