ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
