-- Item 02 — Email lifecycle system.
-- Two tables:
--   email_events       — send + Resend-webhook outcome ledger. One row per
--                        send; webhook handler updates the matching row's
--                        delivered_at / opened_at / clicked_at / bounced_at
--                        / complained_at / unsubscribed_at columns.
--   email_send_history — frequency-cap ledger. Eligibility queries skip
--                        users with any lifecycle send within the cap
--                        window (default 7 days). Lighter than email_events
--                        and indexed for the (user_id, sent_at) lookup
--                        pattern the cron uses on every tick.
--
-- See services/lifecycle_emails.py for the dispatcher and the Resend
-- webhook handler.

CREATE TABLE IF NOT EXISTS email_events (
  id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  variant           VARCHAR(40) NOT NULL,
  sent_at           TIMESTAMP NOT NULL DEFAULT NOW(),
  resend_message_id TEXT UNIQUE,
  delivered_at      TIMESTAMP,
  opened_at         TIMESTAMP,
  clicked_at        TIMESTAMP,
  bounced_at        TIMESTAMP,
  complained_at     TIMESTAMP,
  unsubscribed_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS email_events_user_id_idx           ON email_events (user_id);
CREATE INDEX IF NOT EXISTS email_events_variant_idx           ON email_events (variant);
CREATE INDEX IF NOT EXISTS email_events_sent_at_idx           ON email_events (sent_at);
CREATE INDEX IF NOT EXISTS email_events_resend_message_id_idx ON email_events (resend_message_id);


CREATE TABLE IF NOT EXISTS email_send_history (
  id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sent_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  variant   VARCHAR(40) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_email_send_history_user_sent ON email_send_history (user_id, sent_at);
