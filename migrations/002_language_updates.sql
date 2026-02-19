-- Migration: Language updates and bot_active tracking

-- Add language column to groups table
ALTER TABLE groups ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'en';

-- Update users table default language from 'ru' to 'en'
ALTER TABLE users ALTER COLUMN language SET DEFAULT 'en';

-- Add bot_active column to groups table (for tracking if bot was removed)
ALTER TABLE groups ADD COLUMN IF NOT EXISTS bot_active BOOLEAN DEFAULT TRUE;
