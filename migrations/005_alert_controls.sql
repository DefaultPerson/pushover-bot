-- Personal alerts, quiet hours, blocks, group confirmation

ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_gms BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_start TIME;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_end TIME;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_tz VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_from TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_to TIMESTAMPTZ;

ALTER TABLE groups ADD COLUMN IF NOT EXISTS confirm_gm BOOLEAN DEFAULT FALSE;

-- blocked_id has no FK: a user can block an id the bot has never seen
CREATE TABLE IF NOT EXISTS user_blocks (
    blocker_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id)
);
CREATE INDEX IF NOT EXISTS idx_user_blocks_blocked ON user_blocks(blocked_id);
