-- Memory Service Migration: Create procedural_memories table
-- Version: 003
-- Date: 2025-01-24

-- ====================
-- Procedural Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.procedural_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'procedural',

    -- Content
    content TEXT NOT NULL,

    -- Procedure structure
    skill_type VARCHAR(100) NOT NULL,
    steps JSONB NOT NULL, -- Array of steps with order and description
    prerequisites TEXT[] DEFAULT '{}',

    -- Procedural memory specific
    difficulty_level VARCHAR(50) DEFAULT 'medium' CHECK (difficulty_level IN ('easy', 'medium', 'hard')),
    success_rate FLOAT DEFAULT 0.0 CHECK (success_rate >= 0 AND success_rate <= 1),
    domain VARCHAR(100) NOT NULL,

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

-- Indexes for procedural memories
CREATE INDEX idx_procedural_memories_user_id ON memory.procedural_memories(user_id);
CREATE INDEX idx_procedural_memories_skill_type ON memory.procedural_memories(skill_type);
CREATE INDEX idx_procedural_memories_domain ON memory.procedural_memories(domain);
CREATE INDEX idx_procedural_memories_difficulty ON memory.procedural_memories(difficulty_level);
CREATE INDEX idx_procedural_memories_success_rate ON memory.procedural_memories(success_rate DESC);
CREATE INDEX idx_procedural_memories_created_at ON memory.procedural_memories(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_procedural_memories_updated_at
    BEFORE UPDATE ON memory.procedural_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- Comments
COMMENT ON TABLE memory.procedural_memories IS 'Procedural memories - how-to knowledge and skills with step-by-step procedures';
COMMENT ON COLUMN memory.procedural_memories.id IS 'Memory ID - also used as Qdrant point ID';
COMMENT ON COLUMN memory.procedural_memories.steps IS 'Procedure steps as JSON array with order and description';
