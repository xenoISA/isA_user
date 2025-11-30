-- Document Service Database Schema
-- Migration: 001_create_documents_table
-- Description: Create knowledge_documents and permission_history tables

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS document;

-- ==================== Knowledge Documents Table ====================

CREATE TABLE IF NOT EXISTS document.knowledge_documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    organization_id VARCHAR(64),

    -- Document basic info
    title VARCHAR(500) NOT NULL,
    description TEXT,
    doc_type VARCHAR(32) NOT NULL,
    file_id VARCHAR(64) NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_url TEXT,

    -- Version control
    version INTEGER DEFAULT 1,
    parent_version_id VARCHAR(64),
    is_latest BOOLEAN DEFAULT TRUE,

    -- RAG indexing info
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    chunk_count INTEGER DEFAULT 0,
    chunking_strategy VARCHAR(32) DEFAULT 'semantic',
    indexed_at TIMESTAMP,
    last_updated_at TIMESTAMP,

    -- Authorization
    access_level VARCHAR(32) NOT NULL DEFAULT 'private',
    allowed_users TEXT[],
    allowed_groups TEXT[],
    denied_users TEXT[],

    -- Qdrant collection info
    collection_name VARCHAR(128) DEFAULT 'default',
    point_ids TEXT[],

    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for knowledge_documents
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON document.knowledge_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_organization_id ON document.knowledge_documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_id ON document.knowledge_documents(file_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON document.knowledge_documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON document.knowledge_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_latest ON document.knowledge_documents(is_latest) WHERE is_latest = TRUE;
CREATE INDEX IF NOT EXISTS idx_documents_parent_version ON document.knowledge_documents(parent_version_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON document.knowledge_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON document.knowledge_documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON document.knowledge_documents USING GIN(metadata);

-- ==================== Document Permission History Table ====================

CREATE TABLE IF NOT EXISTS document.document_permission_history (
    history_id SERIAL PRIMARY KEY,
    doc_id VARCHAR(64) NOT NULL,
    changed_by VARCHAR(64) NOT NULL,

    -- Permission changes
    old_access_level VARCHAR(32),
    new_access_level VARCHAR(32),

    -- User/Group changes
    users_added TEXT[],
    users_removed TEXT[],
    groups_added TEXT[],
    groups_removed TEXT[],

    -- Timestamp
    changed_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_document FOREIGN KEY (doc_id)
        REFERENCES document.knowledge_documents(doc_id) ON DELETE CASCADE
);

-- Indexes for permission history
CREATE INDEX IF NOT EXISTS idx_permission_history_doc_id ON document.document_permission_history(doc_id);
CREATE INDEX IF NOT EXISTS idx_permission_history_changed_by ON document.document_permission_history(changed_by);
CREATE INDEX IF NOT EXISTS idx_permission_history_changed_at ON document.document_permission_history(changed_at DESC);

-- ==================== Comments ====================

COMMENT ON TABLE document.knowledge_documents IS 'Knowledge base documents with RAG indexing and permissions';
COMMENT ON COLUMN document.knowledge_documents.doc_id IS 'Unique document identifier';
COMMENT ON COLUMN document.knowledge_documents.version IS 'Document version number (incremented on updates)';
COMMENT ON COLUMN document.knowledge_documents.is_latest IS 'Flag indicating if this is the latest version';
COMMENT ON COLUMN document.knowledge_documents.status IS 'Document indexing status (draft, indexing, indexed, updating, failed)';
COMMENT ON COLUMN document.knowledge_documents.chunk_count IS 'Number of chunks indexed in Qdrant';
COMMENT ON COLUMN document.knowledge_documents.access_level IS 'Access level (private, team, organization, public)';
COMMENT ON COLUMN document.knowledge_documents.allowed_users IS 'User IDs with explicit access';
COMMENT ON COLUMN document.knowledge_documents.allowed_groups IS 'Group IDs with access';
COMMENT ON COLUMN document.knowledge_documents.denied_users IS 'User IDs explicitly denied access';
COMMENT ON COLUMN document.knowledge_documents.point_ids IS 'Qdrant point IDs for this document';

COMMENT ON TABLE document.document_permission_history IS 'Audit trail for document permission changes';

-- ==================== Triggers ====================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION document.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON document.knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION document.update_updated_at_column();
