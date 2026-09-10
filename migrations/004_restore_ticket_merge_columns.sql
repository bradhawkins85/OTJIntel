-- Restore ticket relationship columns used by ticket list, split, and merge queries.
-- They were omitted when the historical migrations were consolidated into 001_init.sql.
ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS merged_into_ticket_id INT NULL;

ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS split_from_ticket_id INT NULL;

CREATE INDEX IF NOT EXISTS idx_tickets_merged_into
  ON tickets (merged_into_ticket_id);

CREATE INDEX IF NOT EXISTS idx_tickets_split_from
  ON tickets (split_from_ticket_id);
