-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Create document metadata table
CREATE TABLE IF NOT EXISTS document_metadata (
    file_hash TEXT PRIMARY KEY,
    doc_path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT,
    tags TEXT[],
    creation_time TIMESTAMP NOT NULL,
    modification_time TIMESTAMP NOT NULL,
    last_indexed_at TIMESTAMP,
    indexing_status TEXT,
    ml_synced BOOLEAN DEFAULT FALSE,
    size BIGINT CHECK (size >= 0),
    metadata JSONB DEFAULT '{}',
    mean_dense_vector vector(1024)
);

-- Create passages table with composite unique constraint
CREATE TABLE IF NOT EXISTS passages (
    passage_id BIGSERIAL PRIMARY KEY,
    file_hash TEXT REFERENCES document_metadata(file_hash) ON DELETE CASCADE,
    -- content TEXT NOT NULL,
    dense_vector vector(1024),
    embedding_model TEXT NOT NULL,
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    window_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_position CHECK (end_pos > start_pos),
    -- A file can have the same passage with different window sizes or models
    CONSTRAINT unique_passage_per_window_and_model UNIQUE (
        file_hash,
        start_pos,
        end_pos,
        window_size
    )
);

-- Create lexical weights table
CREATE TABLE IF NOT EXISTS lexical_weights (
    passage_id BIGINT REFERENCES passages(passage_id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    weight FLOAT NOT NULL,
    window_size INTEGER NOT NULL,
    PRIMARY KEY (passage_id, token, window_size)
);

-- Create document text table
CREATE TABLE IF NOT EXISTS document_texts (
    file_hash TEXT PRIMARY KEY REFERENCES document_metadata(file_hash) ON DELETE CASCADE,
    content TEXT NOT NULL
);

-- Create document versions table
CREATE TABLE IF NOT EXISTS document_versions (
    file_hash TEXT REFERENCES document_metadata(file_hash) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    doc_path TEXT NOT NULL,
    modification_time TIMESTAMP NOT NULL,
    PRIMARY KEY (file_hash, version)
);

-- Create indexing configuration table to track different indexing settings
CREATE TABLE IF NOT EXISTS indexing_configurations (
    config_id SERIAL PRIMARY KEY,
    window_size INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config_params JSONB DEFAULT '{}',
    UNIQUE (window_size, embedding_model)
);

-- Create document indexing status table with reference to configurations
CREATE TABLE IF NOT EXISTS document_indexing_status (
    file_hash TEXT REFERENCES document_metadata(file_hash) ON DELETE CASCADE,
    config_id INTEGER REFERENCES indexing_configurations(config_id),
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL, -- 'completed', 'failed', 'in_progress'
    error_message TEXT,
    passage_count INTEGER,
    PRIMARY KEY (file_hash, config_id)
);

-- Create helpful views
CREATE OR REPLACE VIEW document_indexing_summary AS
SELECT
    dm.file_hash,
    dm.filename,
    dm.doc_path,
    ic.window_size,
    ic.embedding_model,
    dis.status,
    dis.indexed_at,
    dis.passage_count,
    ic.config_params
FROM document_metadata dm
CROSS JOIN indexing_configurations ic
LEFT JOIN document_indexing_status dis
    ON dm.file_hash = dis.file_hash
    AND ic.config_id = dis.config_id;

-- Create helper function to get passages for a document
CREATE OR REPLACE FUNCTION get_document_passages(
    p_file_hash TEXT,
    p_window_size INTEGER DEFAULT NULL,
    p_embedding_model TEXT DEFAULT NULL
) RETURNS TABLE (
    passage_id BIGINT,
    content TEXT,
    start_pos INTEGER,
    end_pos INTEGER,
    window_size INTEGER,
    embedding_model TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.passage_id,
        p.content,
        p.start_pos,
        p.end_pos,
        p.window_size,
        p.embedding_model
    FROM passages p
    WHERE p.file_hash = p_file_hash
    AND (p_window_size IS NULL OR p.window_size = p_window_size)
    AND (p_embedding_model IS NULL OR p.embedding_model = p_embedding_model)
    ORDER BY p.start_pos;
END;
$$
 LANGUAGE plpgsql;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_passages_file_hash_window
    ON passages(file_hash, window_size);
CREATE INDEX IF NOT EXISTS idx_passages_embedding_model
    ON passages(embedding_model);
CREATE INDEX IF NOT EXISTS idx_passages_dense_vector
    ON passages USING ivfflat (dense_vector vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_passages_positions
    ON passages(file_hash, start_pos, end_pos);

-- Create function to add new indexing configuration
CREATE OR REPLACE FUNCTION add_indexing_configuration(
    p_window_size INTEGER,
    p_embedding_model TEXT,
    p_config_params JSONB DEFAULT '{}'
) RETURNS INTEGER AS $$
DECLARE
    v_config_id INTEGER;
BEGIN
    INSERT INTO indexing_configurations (window_size, embedding_model, config_params)
    VALUES (p_window_size, p_embedding_model, p_config_params)
    ON CONFLICT (window_size, embedding_model)
    DO UPDATE SET config_params = p_config_params
    RETURNING config_id INTO v_config_id;

    RETURN v_config_id;
END;
$$
 LANGUAGE plpgsql;
