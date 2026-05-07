-- Short-lived bridge between an OAuth callback (handled by one gunicorn
-- worker) and the SPA's nonce-exchange poll (which can land on a
-- different worker). Process-local dicts can't cross workers; this
-- table can. Rows expire after 300s and are pruned on every write.

CREATE TABLE IF NOT EXISTS oauth_nonces (
  nonce      TEXT PRIMARY KEY,
  token      TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS oauth_nonces_created_at_idx ON oauth_nonces (created_at);
