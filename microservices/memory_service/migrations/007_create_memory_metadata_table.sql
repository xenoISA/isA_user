-- Memory Service Migration: Create memory_metadata table
-- Version: 007
-- Date: 2025-01-24

-- ====================
-- Memory Metadata Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.memory_metadata (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(20) NOT NULL CHECK (memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working', 'session')),
    memory_id VARCHAR(255) NOT NULL,

    -- Access tracking
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    first_accessed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Modification tracking
    modification_count INTEGER DEFAULT 0,
    last_modified_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,

    -- Quality metrics
    accuracy_score FLOAT CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),
    completeness_score FLOAT CHECK (completeness_score >= 0 AND completeness_score <= 1),

    -- User feedback
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    feedback_timestamp TIMESTAMPTZ,

    -- System management
    system_flags JSONB DEFAULT '{}'::jsonb,
    priority_level INTEGER DEFAULT 3 CHECK (priority_level >= 1 AND priority_level <= 5),
    dependency_count INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0,

    -- Lifecycle
    lifecycle_stage VARCHAR(20) DEFAULT 'active' CHECK (lifecycle_stage IN ('active', 'stale', 'deprecated', 'archived')),
    auto_expire BOOLEAN DEFAULT false,
    expire_after_days INTEGER,

    -- Learning metrics
    reinforcement_score FLOAT DEFAULT 0.0,
    learning_curve JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(user_id, memory_type, memory_id)
);

-- Indexes for memory_metadata
CREATE INDEX idx_metadata_user_type ON memory.memory_metadata(user_id, memory_type);
CREATE INDEX idx_metadata_memory ON memory.memory_metadata(memory_type, memory_id);
CREATE INDEX idx_metadata_access ON memory.memory_metadata(access_count DESC);
CREATE INDEX idx_metadata_quality ON memory.memory_metadata(accuracy_score DESC, relevance_score DESC);
CREATE INDEX idx_metadata_priority ON memory.memory_metadata(priority_level DESC);
CREATE INDEX idx_metadata_lifecycle ON memory.memory_metadata(lifecycle_stage);
CREATE INDEX idx_metadata_flags ON memory.memory_metadata USING gin(system_flags);

-- Comments
COMMENT ON TABLE memory.memory_metadata IS 'Memory metadata for tracking usage, quality, and lifecycle of memories';
COMMENT ON COLUMN memory.memory_metadata.memory_id IS 'References the ID in the specific memory type table';
