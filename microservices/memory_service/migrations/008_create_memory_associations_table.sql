-- Memory Service Migration: Create memory_associations table
-- Version: 008
-- Date: 2025-01-24

-- ====================
-- Memory Associations Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.memory_associations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,

    -- Source memory
    source_memory_type VARCHAR(20) NOT NULL CHECK (source_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
    source_memory_id VARCHAR(255) NOT NULL,

    -- Target memory
    target_memory_type VARCHAR(20) NOT NULL CHECK (target_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
    target_memory_id VARCHAR(255) NOT NULL,

    -- Association details
    association_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
    context TEXT,

    -- Discovery and confirmation
    auto_discovered BOOLEAN DEFAULT false,
    confirmation_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(user_id, source_memory_type, source_memory_id, target_memory_type, target_memory_id, association_type)
);

-- Indexes for memory_associations
CREATE INDEX idx_associations_user ON memory.memory_associations(user_id);
CREATE INDEX idx_associations_source ON memory.memory_associations(source_memory_type, source_memory_id);
CREATE INDEX idx_associations_target ON memory.memory_associations(target_memory_type, target_memory_id);
CREATE INDEX idx_associations_strength ON memory.memory_associations(strength DESC);

-- Comments
COMMENT ON TABLE memory.memory_associations IS 'Associations between memories for relationship mapping';
COMMENT ON COLUMN memory.memory_associations.association_type IS 'Type of association: related, caused_by, prerequisite_for, etc.';
COMMENT ON COLUMN memory.memory_associations.strength IS 'Association strength (0-1)';
