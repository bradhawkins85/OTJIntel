-- Permit bootstrap registration before the first company has been configured.
ALTER TABLE users
  MODIFY COLUMN company_id INT NULL;

-- Bring installations created from the older consolidated schema in line with
-- the session repository. Conditional additions make this migration safe for
-- installations that already received some or all of these columns.
ALTER TABLE user_sessions
  ADD COLUMN IF NOT EXISTS active_company_id INT NULL AFTER user_id,
  ADD COLUMN IF NOT EXISTS impersonator_user_id INT NULL AFTER pending_totp_secret,
  ADD COLUMN IF NOT EXISTS impersonator_session_id INT NULL AFTER impersonator_user_id,
  ADD COLUMN IF NOT EXISTS impersonation_started_at DATETIME NULL AFTER impersonator_session_id;
