-- Pushover Bot Database Schema

-- Users (Telegram users)
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    pushover_key VARCHAR(30),
    language VARCHAR(5) DEFAULT 'ru',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Groups (Telegram groups/supergroups)
CREATE TABLE IF NOT EXISTS groups (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    only_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions: user <-> group (M2M)
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, group_id)
);

-- Notification logs (instead of file logs)
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    group_id BIGINT,
    sender_id BIGINT NOT NULL,
    recipient_id BIGINT NOT NULL,
    notification_type VARCHAR(20) NOT NULL,
    pushover_success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rate limiting: /gm call history
CREATE TABLE IF NOT EXISTS gm_history (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    called_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_subscriptions_group ON subscriptions(group_id) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_gm_history_lookup ON gm_history(group_id, called_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_created ON notification_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sender ON notification_logs(sender_id, created_at DESC);
