-- Memory Service Migration: Create episodic_memories table
-- Version: 002
-- Date: 2025-01-24

-- ====================
-- Episodic Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.episodic_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'episodic',

    -- Content
    content TEXT NOT NULL,

    -- Episode structure
    event_type VARCHAR(100) NOT NULL,
    location TEXT,
    participants TEXT[] DEFAULT '{}',

    -- Episodic memory specific
    emotional_valence FLOAT DEFAULT 0.0 CHECK (emotional_valence >= -1 AND emotional_valence <= 1),
    vividness FLOAT DEFAULT 0.5 CHECK (vividness >= 0 AND vividness <= 1),
    episode_date TIMESTAMPTZ,

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

-- Indexes for episodic memories
CREATE INDEX idx_episodic_memories_user_id ON memory.episodic_memories(user_id);
CREATE INDEX idx_episodic_memories_event_type ON memory.episodic_memories(event_type);
CREATE INDEX idx_episodic_memories_location ON memory.episodic_memories USING gin(to_tsvector('english', location));
CREATE INDEX idx_episodic_memories_episode_date ON memory.episodic_memories(episode_date DESC);
CREATE INDEX idx_episodic_memories_emotional_valence ON memory.episodic_memories(emotional_valence);
CREATE INDEX idx_episodic_memories_participants ON memory.episodic_memories USING gin(participants);
CREATE INDEX idx_episodic_memories_created_at ON memory.episodic_memories(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_episodic_memories_updated_at
    BEFORE UPDATE ON memory.episodic_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- Comments
COMMENT ON TABLE memory.episodic_memories IS 'Episodic memories - personal experiences and events with temporal/spatial context';
COMMENT ON COLUMN memory.episodic_memories.id IS 'Memory ID - also used as Qdrant point ID';
COMMENT ON COLUMN memory.episodic_memories.emotional_valence IS 'Emotional tone: -1 (negative) to 1 (positive)';
COMMENT ON COLUMN memory.episodic_memories.vividness IS 'How vivid/detailed the memory is (0-1)';
