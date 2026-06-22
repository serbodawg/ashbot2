-- AshBot 2 tables for Apologia Supabase

CREATE TABLE IF NOT EXISTS ashbot_guild_config (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT UNIQUE NOT NULL,
  prefix TEXT DEFAULT '/',
  automod_enabled BOOLEAN DEFAULT FALSE,
  antilink BOOLEAN DEFAULT TRUE,
  antyraid BOOLEAN DEFAULT TRUE,
  auto_ban_nuke BOOLEAN DEFAULT TRUE,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ashbot_warnings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  moderator_id BIGINT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ashbot_levels (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  xp BIGINT DEFAULT 0,
  level INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ashbot_level_roles (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  level INT NOT NULL,
  role_id BIGINT NOT NULL,
  UNIQUE (guild_id, level)
);

CREATE TABLE IF NOT EXISTS ashbot_advice (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  text TEXT NOT NULL,
  added_by BIGINT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ashbot_bot_whitelist (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  bot_id BIGINT NOT NULL,
  UNIQUE (guild_id, bot_id)
);

CREATE TABLE IF NOT EXISTS ashbot_backups (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ashbot_log_channels (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  log_type TEXT NOT NULL,
  channel_id BIGINT NOT NULL,
  UNIQUE (guild_id, log_type)
);

CREATE TABLE IF NOT EXISTS ashbot_ai_channels (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  UNIQUE (guild_id, channel_id)
);

-- Random advice function
CREATE OR REPLACE FUNCTION public.ashbot_random_advice()
RETURNS TEXT
LANGUAGE sql
AS $$ SELECT text FROM ashbot_advice ORDER BY RANDOM() LIMIT 1; $$;

CREATE TABLE IF NOT EXISTS ashbot_ships (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  guild_id BIGINT NOT NULL,
  shipper_id BIGINT NOT NULL,
  user1_id BIGINT NOT NULL,
  user2_id BIGINT NOT NULL,
  ship_name TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ashbot_warnings_guild ON ashbot_warnings(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_ashbot_levels_guild ON ashbot_levels(guild_id, xp DESC);
CREATE INDEX IF NOT EXISTS idx_ashbot_backups_guild ON ashbot_backups(guild_id);
CREATE INDEX IF NOT EXISTS idx_ashbot_ships_guild ON ashbot_ships(guild_id, created_at DESC);
