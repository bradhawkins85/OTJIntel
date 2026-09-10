-- Restore a table accidentally omitted when the legacy migrations were compacted.
-- This migration repairs installations that already recorded 001_init.sql as applied.
CREATE TABLE IF NOT EXISTS email_tracking_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tracking_id VARCHAR(64) NOT NULL COMMENT 'References ticket_replies.email_tracking_id',
    event_type ENUM('open', 'click', 'delivered', 'bounce', 'spam', 'processed', 'rejected') NOT NULL COMMENT 'Type of tracking event',
    event_url VARCHAR(2048) NULL COMMENT 'URL clicked (for click events)',
    user_agent TEXT NULL COMMENT 'User agent from tracking request',
    ip_address VARCHAR(45) NULL COMMENT 'IP address from tracking request',
    referrer VARCHAR(2048) NULL COMMENT 'Referrer from tracking request',
    occurred_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP) COMMENT 'When the event occurred',
    plausible_sent TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether event was sent to Plausible',
    plausible_sent_at DATETIME NULL COMMENT 'When event was sent to Plausible',
    smtp2go_data TEXT NULL COMMENT 'Full SMTP2Go webhook data (JSON)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX IF NOT EXISTS idx_email_tracking_events_tracking_id ON email_tracking_events (tracking_id);
CREATE INDEX IF NOT EXISTS idx_email_tracking_events_type ON email_tracking_events (event_type);
CREATE INDEX IF NOT EXISTS idx_email_tracking_events_occurred ON email_tracking_events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_email_tracking_events_plausible_sent ON email_tracking_events (plausible_sent);
