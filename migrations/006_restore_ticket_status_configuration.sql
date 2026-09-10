-- Restore ticket status configuration columns used by the admin ticket page.
-- These may be absent when 001_init.sql was recorded before its consolidation
-- included the historical ticket status migrations.
ALTER TABLE ticket_statuses
  ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NOT NULL DEFAULT 0 AFTER public_status;

ALTER TABLE ticket_statuses
  ADD COLUMN IF NOT EXISTS hide_from_technicians TINYINT(1) NOT NULL DEFAULT 0 AFTER is_default;

ALTER TABLE ticket_statuses
  ADD COLUMN IF NOT EXISTS hide_from_admins TINYINT(1) NOT NULL DEFAULT 0 AFTER hide_from_technicians;

CREATE INDEX IF NOT EXISTS idx_ticket_statuses_default
  ON ticket_statuses (is_default);

CREATE INDEX IF NOT EXISTS idx_ticket_statuses_hide_from_technicians
  ON ticket_statuses (hide_from_technicians);

CREATE INDEX IF NOT EXISTS idx_ticket_statuses_hide_from_admins
  ON ticket_statuses (hide_from_admins);
