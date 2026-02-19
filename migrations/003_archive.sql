-- Message archive for groups
CREATE TABLE IF NOT EXISTS archived_messages (
    id SERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    user_id BIGINT,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),

    -- Message content
    text TEXT,
    caption TEXT,

    -- Media info (if any)
    media_type VARCHAR(20),  -- photo, video, document, audio, voice, video_note, sticker, animation
    media_file_id VARCHAR(255),
    media_file_path VARCHAR(500),  -- local path to saved file
    media_file_name VARCHAR(255),  -- original filename
    media_mime_type VARCHAR(100),
    media_file_size BIGINT,

    -- Reply info
    reply_to_message_id BIGINT,

    -- Forward info
    forward_from_user_id BIGINT,
    forward_from_chat_id BIGINT,
    forward_date TIMESTAMPTZ,

    -- Timestamps
    message_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint to avoid duplicates
    UNIQUE (group_id, message_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_archived_messages_group ON archived_messages(group_id, message_date DESC);
CREATE INDEX IF NOT EXISTS idx_archived_messages_user ON archived_messages(user_id, message_date DESC);
CREATE INDEX IF NOT EXISTS idx_archived_messages_date ON archived_messages(message_date DESC);
CREATE INDEX IF NOT EXISTS idx_archived_messages_media ON archived_messages(media_type) WHERE media_type IS NOT NULL;
