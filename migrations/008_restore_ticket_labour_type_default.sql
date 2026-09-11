-- Restore the default flag omitted from the consolidated initial migration.
-- A separate migration identity repairs installations that already recorded 001.
ALTER TABLE ticket_labour_types
  ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NOT NULL DEFAULT 0 AFTER rate;

CREATE INDEX IF NOT EXISTS idx_ticket_labour_types_default
  ON ticket_labour_types (is_default);

-- Preserve an existing default; otherwise select the oldest labour type.
UPDATE ticket_labour_types
SET is_default = 1
WHERE id = (
  SELECT id FROM (
    SELECT id FROM ticket_labour_types
    ORDER BY created_at ASC, id ASC
    LIMIT 1
  ) AS first_labour_type
)
AND NOT EXISTS (
  SELECT 1 FROM ticket_labour_types WHERE is_default = 1
);
