-- Consolidated init migration for retained OTJIntel features.
-- Generated from retained DDL across legacy migrations.

-- Source: 001_init.sql
CREATE TABLE IF NOT EXISTS companies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  address VARCHAR(255)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  company_id INT NOT NULL,
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS licenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  platform VARCHAR(255) NOT NULL,
  count INT NOT NULL,
  expiry_date DATE,
  contract_term VARCHAR(255),
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 002_user_companies.sql
CREATE TABLE IF NOT EXISTS user_companies (
  user_id INT NOT NULL,
  company_id INT NOT NULL,
  can_manage_licenses TINYINT(1) DEFAULT 0,
  can_manage_staff TINYINT(1) DEFAULT 0,
  PRIMARY KEY (user_id, company_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 003_staff.sql
CREATE TABLE IF NOT EXISTS staff (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  date_onboarded DATE,
  enabled TINYINT(1) DEFAULT 1,
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 004_add_can_manage_staff.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_manage_staff TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_manage_staff TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 005_api_keys.sql
CREATE TABLE IF NOT EXISTS api_keys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  api_key VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(255),
  expiry_date DATE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 006_staff_licenses.sql
CREATE TABLE IF NOT EXISTS staff_licenses (
  staff_id INT NOT NULL,
  license_id INT NOT NULL,
  PRIMARY KEY (staff_id, license_id),
  FOREIGN KEY (staff_id) REFERENCES staff(id),
  FOREIGN KEY (license_id) REFERENCES licenses(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 007_add_asset_invoice_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_manage_assets TINYINT(1),
  ADD COLUMN IF NOT EXISTS can_manage_invoices TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_manage_assets TINYINT(1) DEFAULT 0 NOT NULL,
  MODIFY can_manage_invoices TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 008_assets.sql
CREATE TABLE IF NOT EXISTS assets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  type VARCHAR(255),
  serial_number VARCHAR(255),
  status VARCHAR(255),
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 011_add_company_admin.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS is_admin TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 011_asset_details.sql
ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS os_name VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS cpu_name VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS ram_gb INT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS hdd_size VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS last_sync DATETIME DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS motherboard_manufacturer VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS form_factor VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS last_user VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS approx_age INT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS performance_score INT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS warranty_status VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS warranty_end_date DATE DEFAULT NULL;

-- Source: 012_apps.sql
CREATE TABLE IF NOT EXISTS apps (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  default_price DECIMAL(10,2) NOT NULL,
  contract_term VARCHAR(255) NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_app_prices (
  company_id INT NOT NULL,
  app_id INT NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (company_id, app_id),
  FOREIGN KEY (company_id) REFERENCES companies(id),
  FOREIGN KEY (app_id) REFERENCES apps(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_order_licenses TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_order_licenses TINYINT(1) DEFAULT 0 NOT NULL;

ALTER TABLE external_api_settings
  ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(255),
  ADD COLUMN IF NOT EXISTS webhook_api_key VARCHAR(255);

-- Source: 013_shop.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_access_shop TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_access_shop TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 017_add_vip_flag_and_vip_price.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_vip TINYINT(1) DEFAULT 0;

-- Source: 022_add_syncro_xero_ids.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS syncro_company_id VARCHAR(255);

ALTER TABLE companies ADD COLUMN IF NOT EXISTS xero_id VARCHAR(255);

-- Source: 025_office_groups.sql
CREATE TABLE IF NOT EXISTS office_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS office_group_members (
  group_id INT NOT NULL,
  staff_id INT NOT NULL,
  PRIMARY KEY (group_id, staff_id),
  FOREIGN KEY (group_id) REFERENCES office_groups(id) ON DELETE CASCADE,
  FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 025_staff_details.sql
ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS street VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS city VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS state VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS postcode VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS country VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS department VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS job_title VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS org_company VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS manager_name VARCHAR(255) NULL;

-- Source: 026_audit_logs.sql
CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  action VARCHAR(255) NOT NULL,
  previous_value TEXT NULL,
  new_value TEXT NULL,
  api_key VARCHAR(64) NULL,
  ip_address VARCHAR(45) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 027_api_key_usage.sql
CREATE TABLE IF NOT EXISTS api_key_usage (
  api_key_id INT NOT NULL,
  ip_address VARCHAR(45) NOT NULL,
  usage_count INT NOT NULL DEFAULT 1,
  last_used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (api_key_id, ip_address),
  FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 028_staff_offboard_date.sql
ALTER TABLE staff
  MODIFY date_onboarded DATETIME NULL,
  ADD COLUMN IF NOT EXISTS date_offboarded DATETIME NULL;

-- Source: 029_staff_account_action.sql
ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS account_action VARCHAR(50) NULL;

-- Source: 030_add_totp_secret.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255);

-- Source: 031_totp_authenticators.sql
CREATE TABLE IF NOT EXISTS user_totp_authenticators (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  secret VARCHAR(255) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE users DROP COLUMN totp_secret;

-- Source: 032_add_company_id_to_audit_logs.sql
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS company_id INT NULL AFTER user_id,
  ADD INDEX idx_audit_logs_company_id (company_id);

-- Source: 033_add_mobile_phone_to_staff.sql
ALTER TABLE staff ADD COLUMN IF NOT EXISTS mobile_phone VARCHAR(20);

-- Source: 034_staff_verification_codes.sql
CREATE TABLE IF NOT EXISTS staff_verification_codes (
  staff_id INT PRIMARY KEY,
  code VARCHAR(6) NOT NULL,
  created_at DATETIME NOT NULL,
  FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 035_add_user_names.sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS first_name VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS last_name VARCHAR(255) NULL;

-- Source: 036_add_admin_name_to_verification_codes.sql
ALTER TABLE staff_verification_codes
  ADD COLUMN IF NOT EXISTS admin_name VARCHAR(255) NULL;

-- Source: 037_site_settings.sql
CREATE TABLE IF NOT EXISTS site_settings (
  id INT PRIMARY KEY,
  company_name VARCHAR(255),
  login_logo LONGTEXT,
  sidebar_logo LONGTEXT
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 038_force_password_change.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS force_password_change TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 039_email_templates.sql
CREATE TABLE IF NOT EXISTS email_templates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 044_add_mobile_phone_to_users.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile_phone VARCHAR(20);

-- Source: 045_add_syncro_contact_id_to_staff.sql
ALTER TABLE staff ADD COLUMN IF NOT EXISTS syncro_contact_id VARCHAR(255);

-- Source: 046_scheduled_tasks.sql
CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NULL,
  name VARCHAR(255) NOT NULL,
  command VARCHAR(100) NOT NULL,
  cron VARCHAR(100) NOT NULL,
  last_run_at DATETIME NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 047_staff_office_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS staff_permission TINYINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS can_manage_office_groups TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 048_password_tokens.sql
CREATE TABLE IF NOT EXISTS password_tokens (
  token VARCHAR(64) PRIMARY KEY,
  user_id INT NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 049_cascade_user_delete.sql
ALTER TABLE user_companies
  DROP FOREIGN KEY user_companies_ibfk_1,
  ADD CONSTRAINT fk_user_companies_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Source: 050_add_favicon_to_site_settings.sql
ALTER TABLE site_settings ADD COLUMN IF NOT EXISTS favicon LONGTEXT;

-- Source: 050_company_section_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_access_cart TINYINT(1),
  ADD COLUMN IF NOT EXISTS can_access_orders TINYINT(1),
  ADD COLUMN IF NOT EXISTS can_access_forms TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_access_cart TINYINT(1) DEFAULT 0 NOT NULL,
  MODIFY can_access_orders TINYINT(1) DEFAULT 0 NOT NULL,
  MODIFY can_access_forms TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 055_company_m365_credentials.sql
CREATE TABLE IF NOT EXISTS company_m365_credentials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL UNIQUE,
  tenant_id VARCHAR(255) NOT NULL,
  client_id VARCHAR(255) NOT NULL,
  client_secret TEXT NOT NULL,
  refresh_token TEXT NULL,
  access_token TEXT NULL,
  token_expires_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 056_add_vendor_sku_to_apps.sql
ALTER TABLE apps
  ADD COLUMN IF NOT EXISTS vendor_sku VARCHAR(255);

-- Source: 057_app_price_options.sql
CREATE TABLE IF NOT EXISTS app_price_options (
  id INT AUTO_INCREMENT PRIMARY KEY,
  app_id INT NOT NULL,
  payment_term ENUM('monthly','annual') NOT NULL,
  contract_term ENUM('monthly','annual') NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  UNIQUE KEY uniq_app_term (app_id, payment_term, contract_term),
  FOREIGN KEY (app_id) REFERENCES apps(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE company_app_prices
  ADD COLUMN IF NOT EXISTS payment_term ENUM('monthly','annual') NOT NULL DEFAULT 'monthly',
  ADD COLUMN IF NOT EXISTS contract_term ENUM('monthly','annual') NOT NULL DEFAULT 'monthly';

ALTER TABLE apps
  DROP COLUMN IF EXISTS default_price,
  DROP COLUMN IF EXISTS contract_term;

-- Source: 058_m365_default_apps.sql
ALTER TABLE apps
  ADD COLUMN IF NOT EXISTS license_sku_id VARCHAR(255);

-- Source: 059_product_price_alerts.sql
ALTER TABLE product_price_alerts
  ADD INDEX idx_product_price_alerts_product_resolved (product_id, resolved_at);

-- Source: 062_security_enhancements.sql
CREATE TABLE IF NOT EXISTS user_sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  session_token CHAR(64) NOT NULL UNIQUE,
  csrf_token CHAR(64) NOT NULL,
  created_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  last_seen_at DATETIME NOT NULL,
  ip_address VARCHAR(45) NULL,
  user_agent VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  pending_totp_secret TEXT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_rate_limits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  identifier VARCHAR(255) NOT NULL UNIQUE,
  window_start DATETIME NOT NULL,
  attempts INT NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_super_admin TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 063_roles_and_memberships.sql
CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT NULL,
  permissions JSON NULL,
  is_system TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_memberships (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  user_id INT NOT NULL,
  role_id INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  invited_by INT NULL,
  invited_at DATETIME NULL,
  joined_at DATETIME NULL,
  last_seen_at DATETIME NULL,
  UNIQUE KEY uq_company_memberships_company_user (company_id, user_id),
  CONSTRAINT fk_company_memberships_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  CONSTRAINT fk_company_memberships_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_company_memberships_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT,
  CONSTRAINT fk_company_memberships_invited_by FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 064_extend_audit_logs.sql
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100) NULL AFTER action,
  ADD COLUMN IF NOT EXISTS entity_id INT NULL AFTER entity_type,
  ADD COLUMN IF NOT EXISTS metadata JSON NULL AFTER new_value;

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Source: 065_port_catalogue.sql
CREATE TABLE IF NOT EXISTS ports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    region VARCHAR(100) NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    description TEXT NULL,
    latitude DECIMAL(9,6) NULL,
    longitude DECIMAL(9,6) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ports_code (code),
    KEY idx_ports_country (country),
    KEY idx_ports_is_active (is_active)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS port_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    port_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    content_type VARCHAR(255) NULL,
    file_size BIGINT NOT NULL,
    description VARCHAR(255) NULL,
    uploaded_by INT NULL,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (port_id) REFERENCES ports (id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE SET NULL,
    KEY idx_port_documents_port_id (port_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS port_pricing_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    port_id INT NOT NULL,
    version_label VARCHAR(100) NOT NULL,
    status ENUM('draft','pending_review','approved','rejected') NOT NULL DEFAULT 'draft',
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    base_rate DECIMAL(12,2) NOT NULL DEFAULT 0,
    handling_rate DECIMAL(12,2) NOT NULL DEFAULT 0,
    storage_rate DECIMAL(12,2) NOT NULL DEFAULT 0,
    notes TEXT NULL,
    submitted_by INT NULL,
    approved_by INT NULL,
    submitted_at TIMESTAMP NULL,
    approved_at TIMESTAMP NULL,
    rejection_reason TEXT NULL,
    effective_from DATE NULL,
    effective_to DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (port_id) REFERENCES ports (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE SET NULL,
    UNIQUE KEY uq_port_pricing_version_label (port_id, version_label),
    KEY idx_port_pricing_status (status),
    KEY idx_port_pricing_effective_from (effective_from)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    event_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    metadata JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    KEY idx_notifications_user_id (user_id),
    KEY idx_notifications_read_at (read_at)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 067_enhance_api_keys.sql
ALTER TABLE api_keys
    MODIFY api_key VARCHAR(128) NOT NULL;

ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS key_prefix VARCHAR(16) NULL AFTER api_key,
    ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_used_at DATETIME NULL AFTER created_at;

CREATE INDEX idx_api_keys_created_at ON api_keys (created_at);

CREATE INDEX idx_api_keys_expiry_date ON api_keys (expiry_date);

CREATE INDEX idx_api_keys_last_used_at ON api_keys (last_used_at);

-- Source: 067_scheduler_monitoring.sql
ALTER TABLE scheduled_tasks
  ADD COLUMN IF NOT EXISTS description TEXT NULL,
  ADD COLUMN IF NOT EXISTS max_retries INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS retry_backoff_seconds INT NOT NULL DEFAULT 300,
  ADD COLUMN IF NOT EXISTS last_status VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS last_error TEXT NULL;

CREATE TABLE IF NOT EXISTS scheduled_task_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  task_id INT NOT NULL,
  status VARCHAR(20) NOT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  duration_ms INT NULL,
  details TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS webhook_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  target_url VARCHAR(500) NOT NULL,
  headers JSON NULL,
  payload JSON NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  response_status INT NULL,
  response_body TEXT NULL,
  attempt_count INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 3,
  backoff_seconds INT NOT NULL DEFAULT 300,
  next_attempt_at DATETIME NULL,
  last_error TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS webhook_event_attempts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  attempt_number INT NOT NULL,
  status VARCHAR(20) NOT NULL,
  response_status INT NULL,
  response_body TEXT NULL,
  error_message TEXT NULL,
  attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES webhook_events(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_webhook_events_status_next_attempt
  ON webhook_events (status, next_attempt_at);

-- Source: 069_notification_preferences.sql
CREATE TABLE IF NOT EXISTS notification_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    channel_in_app TINYINT(1) NOT NULL DEFAULT 1,
    channel_email TINYINT(1) NOT NULL DEFAULT 0,
    channel_sms TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_preferences_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE KEY uq_notification_preferences_user_event (user_id, event_type)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 070_tickets_automations_modules.sql
CREATE TABLE IF NOT EXISTS tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NULL,
    requester_id INT NULL,
    assigned_user_id INT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    status_changed_at DATETIME(6) NULL,
    priority VARCHAR(32) NOT NULL DEFAULT 'normal',
    category VARCHAR(64) NULL,
    module_slug VARCHAR(64) NULL,
    external_reference VARCHAR(128) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    closed_at DATETIME(6) NULL,
    INDEX idx_tickets_company_id (company_id),
    INDEX idx_tickets_requester_id (requester_id),
    INDEX idx_tickets_assigned_user_id (assigned_user_id),
    INDEX idx_tickets_status (status),
    INDEX idx_tickets_module_slug (module_slug),
    CONSTRAINT fk_tickets_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
    CONSTRAINT fk_tickets_requester FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_tickets_assigned FOREIGN KEY (assigned_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_replies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    author_id INT NULL,
    body TEXT NOT NULL,
    is_internal TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_ticket_replies_ticket_id (ticket_id),
    INDEX idx_ticket_replies_author_id (author_id),
    CONSTRAINT fk_ticket_replies_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_replies_author FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_watchers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_ticket_watchers_ticket_user (ticket_id, user_id),
    CONSTRAINT fk_ticket_watchers_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_watchers_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS automations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    kind VARCHAR(32) NOT NULL,
    cadence VARCHAR(64) NULL,
    cron_expression VARCHAR(255) NULL,
    trigger_event VARCHAR(128) NULL,
    trigger_filters JSON NULL,
    action_module VARCHAR(64) NULL,
    action_payload JSON NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'inactive',
    next_run_at DATETIME(6) NULL,
    last_run_at DATETIME(6) NULL,
    last_error TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_automations_kind (kind),
    INDEX idx_automations_status (status),
    INDEX idx_automations_next_run (next_run_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS automation_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    automation_id INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    finished_at DATETIME(6) NULL,
    duration_ms BIGINT UNSIGNED NULL,
    result_payload JSON NULL,
    error_message TEXT NULL,
    CONSTRAINT fk_automation_runs_automation FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_modules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    icon VARCHAR(32) NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 0,
    settings JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE integration_modules
    MODIFY settings JSON NOT NULL DEFAULT (JSON_OBJECT());

-- Source: 071_knowledge_base.sql
CREATE TABLE IF NOT EXISTS knowledge_base_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(191) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    summary TEXT NULL,
    content LONGTEXT NOT NULL,
    permission_scope ENUM('anonymous','user','company','company_admin','super_admin') NOT NULL DEFAULT 'anonymous',
    is_published TINYINT(1) NOT NULL DEFAULT 0,
    published_at DATETIME(6) NULL,
    created_by INT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_knowledge_base_articles_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_base_article_users (
    article_id INT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (article_id, user_id),
    CONSTRAINT fk_kb_article_users_article FOREIGN KEY (article_id) REFERENCES knowledge_base_articles(id) ON DELETE CASCADE,
    CONSTRAINT fk_kb_article_users_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_base_article_companies (
    article_id INT NOT NULL,
    company_id INT NOT NULL,
    require_admin TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (article_id, company_id, require_admin),
    CONSTRAINT fk_kb_article_companies_article FOREIGN KEY (article_id) REFERENCES knowledge_base_articles(id) ON DELETE CASCADE,
    CONSTRAINT fk_kb_article_companies_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_kb_articles_published_scope ON knowledge_base_articles (is_published, permission_scope);

CREATE INDEX idx_kb_articles_updated_at ON knowledge_base_articles (updated_at);

-- Source: 072_knowledge_base_sections.sql
CREATE TABLE IF NOT EXISTS knowledge_base_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    position INT NOT NULL,
    heading VARCHAR(255) NULL,
    content LONGTEXT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_kb_sections_article FOREIGN KEY (article_id) REFERENCES knowledge_base_articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_kb_sections_article_position ON knowledge_base_sections (article_id, position);

-- Source: 073_ticket_ai_summary.sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS ai_summary TEXT NULL AFTER description,
    ADD COLUMN IF NOT EXISTS ai_summary_status VARCHAR(32) NULL AFTER ai_summary,
    ADD COLUMN IF NOT EXISTS ai_summary_model VARCHAR(128) NULL AFTER ai_summary_status,
    ADD COLUMN IF NOT EXISTS ai_resolution_state VARCHAR(32) NULL AFTER ai_summary_model,
    ADD COLUMN IF NOT EXISTS ai_summary_updated_at DATETIME(6) NULL AFTER ai_resolution_state;

-- Source: 074_knowledge_base_ai_tags.sql
ALTER TABLE knowledge_base_articles
    ADD COLUMN IF NOT EXISTS ai_tags JSON NULL AFTER summary;

-- Source: 074_ticket_ai_tags.sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS ai_tags JSON NULL AFTER ai_summary_updated_at,
    ADD COLUMN IF NOT EXISTS ai_tags_status VARCHAR(32) NULL AFTER ai_tags,
    ADD COLUMN IF NOT EXISTS ai_tags_model VARCHAR(128) NULL AFTER ai_tags_status,
    ADD COLUMN IF NOT EXISTS ai_tags_updated_at DATETIME(6) NULL AFTER ai_tags_model;

-- Source: 077_webhook_request_logging.sql
ALTER TABLE webhook_event_attempts
  ADD COLUMN IF NOT EXISTS request_headers TEXT NULL;

ALTER TABLE webhook_event_attempts
  ADD COLUMN IF NOT EXISTS request_body TEXT NULL;

ALTER TABLE webhook_event_attempts
  ADD COLUMN IF NOT EXISTS response_headers TEXT NULL;

-- Source: 078_syncro_ticket_reply_enhancements.sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS ticket_number VARCHAR(64) NULL AFTER external_reference;

ALTER TABLE ticket_replies
    ADD COLUMN IF NOT EXISTS external_reference VARCHAR(128) NULL AFTER body,
    ADD UNIQUE KEY uq_ticket_replies_external (ticket_id, external_reference);

-- Source: 079_change_log.sql
CREATE TABLE IF NOT EXISTS change_log (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    guid CHAR(36) NOT NULL,
    occurred_at_utc DATETIME(6) NOT NULL,
    change_type VARCHAR(32) NOT NULL,
    summary TEXT NOT NULL,
    source_file VARCHAR(255) NULL,
    content_hash CHAR(64) NOT NULL,
    created_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uniq_change_log_guid (guid),
    UNIQUE KEY uniq_change_log_hash (content_hash),
    KEY idx_change_log_occurred_at (occurred_at_utc),
    KEY idx_change_log_type (change_type)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 080_company_email_domains.sql
CREATE TABLE IF NOT EXISTS company_email_domains (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    company_id INT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_company_email_domains_company FOREIGN KEY (company_id)
        REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT uq_company_email_domains_domain UNIQUE KEY (domain),
    INDEX idx_company_email_domains_company (company_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 082_imap_accounts.sql
CREATE TABLE IF NOT EXISTS imap_accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NULL,
  name VARCHAR(255) NOT NULL,
  host VARCHAR(255) NOT NULL,
  port SMALLINT NOT NULL DEFAULT 993,
  username VARCHAR(255) NOT NULL,
  password_encrypted TEXT NOT NULL,
  folder VARCHAR(255) NOT NULL DEFAULT 'INBOX',
  process_unread_only TINYINT(1) NOT NULL DEFAULT 1,
  mark_as_read TINYINT(1) NOT NULL DEFAULT 1,
  schedule_cron VARCHAR(100) NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  scheduled_task_id INT NULL,
  last_synced_at DATETIME NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NULL DEFAULT NULL,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
  FOREIGN KEY (scheduled_task_id) REFERENCES scheduled_tasks(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS imap_account_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  message_uid VARCHAR(255) NOT NULL,
  ticket_id INT NULL,
  status VARCHAR(32) NOT NULL,
  error TEXT NULL,
  processed_at DATETIME NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_imap_account_messages_account_uid (account_id, message_uid),
  FOREIGN KEY (account_id) REFERENCES imap_accounts(id) ON DELETE CASCADE,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 083_imap_priority.sql
ALTER TABLE imap_accounts
    ADD COLUMN IF NOT EXISTS priority SMALLINT NOT NULL DEFAULT 100 AFTER id;

-- Source: 084_imap_filters.sql
ALTER TABLE imap_accounts
  ADD COLUMN IF NOT EXISTS filter_query TEXT NULL AFTER schedule_cron;

-- Source: 085_ticket_reply_time_tracking.sql
ALTER TABLE ticket_replies
    ADD COLUMN IF NOT EXISTS minutes_spent INT NULL;

ALTER TABLE ticket_replies
    ADD COLUMN IF NOT EXISTS is_billable TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 087_issue_tracker.sql
CREATE TABLE IF NOT EXISTS issue_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    created_by INT NULL,
    updated_by INT NULL,
    created_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uniq_issue_definitions_name (name),
    KEY idx_issue_definitions_created_at (created_at_utc),
    CONSTRAINT fk_issue_definitions_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_issue_definitions_updated_by FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS issue_company_statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    company_id INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    notes TEXT NULL,
    updated_by INT NULL,
    created_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uniq_issue_company (issue_id, company_id),
    KEY idx_issue_company_status (status),
    KEY idx_issue_company_updated_at (updated_at_utc),
    CONSTRAINT fk_issue_company_issue FOREIGN KEY (issue_id) REFERENCES issue_definitions(id) ON DELETE CASCADE,
    CONSTRAINT fk_issue_company_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_issue_company_updated_by FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 087_ticket_statuses.sql
CREATE TABLE IF NOT EXISTS ticket_statuses (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    tech_status VARCHAR(64) NOT NULL,
    tech_label VARCHAR(128) NOT NULL,
    public_status VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_ticket_statuses_status (tech_status)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 088_pending_staff_access.sql
CREATE TABLE IF NOT EXISTS pending_staff_access (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    staff_id INT NOT NULL,
    company_id INT NOT NULL,
    staff_permission TINYINT NOT NULL DEFAULT 0,
    can_manage_staff TINYINT NOT NULL DEFAULT 0,
    can_manage_licenses TINYINT NOT NULL DEFAULT 0,
    can_manage_assets TINYINT NOT NULL DEFAULT 0,
    can_manage_invoices TINYINT NOT NULL DEFAULT 0,
    can_manage_office_groups TINYINT NOT NULL DEFAULT 0,
    can_order_licenses TINYINT NOT NULL DEFAULT 0,
    can_access_shop TINYINT NOT NULL DEFAULT 0,
    can_access_cart TINYINT NOT NULL DEFAULT 0,
    can_access_orders TINYINT NOT NULL DEFAULT 0,
    can_access_forms TINYINT NOT NULL DEFAULT 0,
    is_admin TINYINT NOT NULL DEFAULT 0,
    role_id INT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uniq_pending_staff_company (staff_id, company_id),
    CONSTRAINT fk_pending_staff_access_staff FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT fk_pending_staff_access_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_pending_staff_access_role FOREIGN KEY (role_id) REFERENCES roles(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 089_api_key_permissions.sql
CREATE TABLE IF NOT EXISTS api_key_endpoint_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    api_key_id INT NOT NULL,
    route VARCHAR(255) NOT NULL,
    method VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_api_key_endpoint_permissions (api_key_id, route, method),
    CONSTRAINT fk_api_key_endpoint_permissions_key
        FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_api_key_endpoint_permissions_route
    ON api_key_endpoint_permissions (route);

CREATE INDEX idx_api_key_endpoint_permissions_method
    ON api_key_endpoint_permissions (method);

-- Source: 090_api_key_ip_restrictions.sql
CREATE TABLE IF NOT EXISTS api_key_ip_restrictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    api_key_id INT NOT NULL,
    cidr VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_api_key_ip_restrictions (api_key_id, cidr),
    CONSTRAINT fk_api_key_ip_restrictions_key
        FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_api_key_ip_restrictions_cidr
    ON api_key_ip_restrictions (cidr);

-- Source: 091_api_key_enable_toggle.sql
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT 1;

CREATE INDEX idx_api_keys_is_enabled ON api_keys (is_enabled);

-- Source: 091_message_templates.sql
CREATE TABLE IF NOT EXISTS message_templates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(120) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  content_type VARCHAR(40) NOT NULL DEFAULT 'text/plain',
  content LONGTEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 095_issue_tracker_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_manage_issues TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_manage_issues TINYINT(1) DEFAULT 0 NOT NULL;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_manage_issues TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_manage_issues TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 095_notification_event_settings.sql
CREATE TABLE IF NOT EXISTS notification_event_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(150) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    message_template TEXT NOT NULL,
    is_user_visible TINYINT(1) NOT NULL DEFAULT 1,
    allow_channel_in_app TINYINT(1) NOT NULL DEFAULT 1,
    allow_channel_email TINYINT(1) NOT NULL DEFAULT 0,
    allow_channel_sms TINYINT(1) NOT NULL DEFAULT 0,
    default_channel_in_app TINYINT(1) NOT NULL DEFAULT 1,
    default_channel_email TINYINT(1) NOT NULL DEFAULT 0,
    default_channel_sms TINYINT(1) NOT NULL DEFAULT 0,
    module_actions JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_notification_event_settings_event_type (event_type)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 096_ticket_labour_types.sql
CREATE TABLE ticket_labour_types (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT UTC_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT UTC_TIMESTAMP(6),
    UNIQUE KEY uq_ticket_labour_code (code)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE ticket_replies
    ADD COLUMN IF NOT EXISTS labour_type_id INT NULL AFTER minutes_spent;

ALTER TABLE ticket_replies
    ADD CONSTRAINT fk_ticket_replies_labour_type
    FOREIGN KEY (labour_type_id) REFERENCES ticket_labour_types(id)
    ON DELETE SET NULL;

CREATE INDEX idx_ticket_replies_labour_type
    ON ticket_replies(labour_type_id);

-- Source: 097_tacticalrmm_assets.sql
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS tacticalrmm_client_id VARCHAR(255) DEFAULT NULL,
  ADD KEY companies_tacticalrmm_client_id (tacticalrmm_client_id);

ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS tactical_asset_id VARCHAR(255) DEFAULT NULL,
  ADD UNIQUE KEY assets_company_tactical_id (company_id, tactical_asset_id);

CREATE TABLE IF NOT EXISTS ticket_assets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id INT NOT NULL,
  asset_id INT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY ticket_asset_unique (ticket_id, asset_id),
  CONSTRAINT fk_ticket_assets_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  CONSTRAINT fk_ticket_assets_asset FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 098_increase_response_body_size.sql
ALTER TABLE webhook_events
  MODIFY COLUMN response_body MEDIUMTEXT NULL;

ALTER TABLE webhook_event_attempts
  MODIFY COLUMN response_body MEDIUMTEXT NULL;

-- Source: 099_asset_custom_fields.sql
CREATE TABLE IF NOT EXISTS asset_custom_field_definitions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  field_type ENUM('text', 'image', 'checkbox', 'url', 'date') NOT NULL,
  display_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_name (name)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_custom_field_values (
  id INT AUTO_INCREMENT PRIMARY KEY,
  asset_id INT NOT NULL,
  field_definition_id INT NOT NULL,
  value_text TEXT,
  value_date DATE,
  value_boolean BOOLEAN,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
  FOREIGN KEY (field_definition_id) REFERENCES asset_custom_field_definitions(id) ON DELETE CASCADE,
  UNIQUE KEY unique_asset_field (asset_id, field_definition_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 099_ticket_tasks.sql
CREATE TABLE IF NOT EXISTS ticket_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    completed_at DATETIME(6) NULL,
    completed_by INT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_ticket_tasks_ticket_id (ticket_id),
    INDEX idx_ticket_tasks_sort_order (sort_order),
    CONSTRAINT fk_ticket_tasks_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_tasks_completed_by FOREIGN KEY (completed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 100_tag_exclusions.sql
CREATE TABLE IF NOT EXISTS tag_exclusions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tag_slug VARCHAR(48) NOT NULL UNIQUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    created_by INT NULL,
    INDEX idx_tag_slug (tag_slug),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 101_knowledge_base_excluded_ai_tags.sql
ALTER TABLE knowledge_base_articles
    ADD COLUMN IF NOT EXISTS excluded_ai_tags JSON NULL AFTER ai_tags;

-- Source: 102_add_issue_slug.sql
ALTER TABLE issue_definitions
  ADD COLUMN IF NOT EXISTS slug VARCHAR(255) NULL;

CREATE UNIQUE INDEX uniq_issue_definitions_slug 
  ON issue_definitions (slug);

-- Source: 109_ticket_xero_billing.sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS xero_invoice_number VARCHAR(64) NULL AFTER closed_at,
    ADD COLUMN IF NOT EXISTS billed_at DATETIME(6) NULL AFTER xero_invoice_number;

CREATE INDEX idx_tickets_xero_invoice ON tickets(xero_invoice_number);

CREATE INDEX idx_tickets_billed_at ON tickets(billed_at);

-- Source: 110_ticket_views.sql
CREATE TABLE IF NOT EXISTS ticket_views (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    filters JSON NULL,
    grouping_field VARCHAR(64) NULL,
    sort_field VARCHAR(64) NULL,
    sort_direction VARCHAR(4) NULL,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_ticket_views_user_id (user_id),
    INDEX idx_ticket_views_default (user_id, is_default),
    CONSTRAINT fk_ticket_views_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 112_add_archived_to_companies.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS archived TINYINT(1) DEFAULT 0 AFTER xero_id;

-- Source: 122_business_continuity_plans.sql
CREATE TABLE IF NOT EXISTS business_continuity_plans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  plan_type ENUM('disaster_recovery', 'incident_response', 'business_continuity') NOT NULL,
  content LONGTEXT NOT NULL,
  version VARCHAR(50) DEFAULT '1.0',
  status ENUM('draft', 'active', 'archived') DEFAULT 'draft',
  created_by INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_reviewed_at DATETIME,
  last_reviewed_by INT,
  FOREIGN KEY (created_by) REFERENCES users(id),
  FOREIGN KEY (last_reviewed_by) REFERENCES users(id),
  INDEX idx_plan_type (plan_type),
  INDEX idx_status (status),
  INDEX idx_created_by (created_by)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS business_continuity_plan_permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  user_id INT,
  company_id INT,
  permission_level ENUM('read', 'edit') NOT NULL DEFAULT 'read',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES business_continuity_plans(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user_plan (plan_id, user_id),
  UNIQUE KEY unique_company_plan (plan_id, company_id),
  INDEX idx_plan_id (plan_id),
  INDEX idx_user_id (user_id),
  INDEX idx_company_id (company_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 122_essential8_compliance.sql
CREATE TABLE IF NOT EXISTS essential8_controls (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  control_order INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_control_order (control_order)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_essential8_compliance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  control_id INT NOT NULL,
  status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant') DEFAULT 'not_started',
  maturity_level ENUM('ml0', 'ml1', 'ml2', 'ml3') DEFAULT 'ml0',
  evidence TEXT,
  notes TEXT,
  last_reviewed_date DATE,
  target_compliance_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (control_id) REFERENCES essential8_controls(id) ON DELETE CASCADE,
  UNIQUE KEY unique_company_control (company_id, control_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_essential8_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  compliance_id INT NOT NULL,
  company_id INT NOT NULL,
  control_id INT NOT NULL,
  user_id INT,
  action VARCHAR(50) NOT NULL,
  old_status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant'),
  new_status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant'),
  old_maturity_level ENUM('ml0', 'ml1', 'ml2', 'ml3'),
  new_maturity_level ENUM('ml0', 'ml1', 'ml2', 'ml3'),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (compliance_id) REFERENCES company_essential8_compliance(id) ON DELETE CASCADE,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (control_id) REFERENCES essential8_controls(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_company_id (company_id),
  INDEX idx_control_id (control_id),
  INDEX idx_created_at (created_at)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 123_essential8_requirements.sql
CREATE TABLE IF NOT EXISTS essential8_requirements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  control_id INT NOT NULL,
  maturity_level ENUM('ml1', 'ml2', 'ml3') NOT NULL,
  requirement_order INT NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (control_id) REFERENCES essential8_controls(id) ON DELETE CASCADE,
  INDEX idx_control_maturity (control_id, maturity_level),
  INDEX idx_requirement_order (control_id, maturity_level, requirement_order)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_essential8_requirement_compliance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  requirement_id INT NOT NULL,
  status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant', 'not_applicable') DEFAULT 'not_started',
  evidence TEXT,
  notes TEXT,
  last_reviewed_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (requirement_id) REFERENCES essential8_requirements(id) ON DELETE CASCADE,
  UNIQUE KEY unique_company_requirement (company_id, requirement_id),
  INDEX idx_company_status (company_id, status)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 124_add_not_applicable_status.sql
ALTER TABLE company_essential8_compliance 
MODIFY COLUMN status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant', 'not_applicable') DEFAULT 'not_started';

ALTER TABLE company_essential8_audit 
MODIFY COLUMN old_status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant', 'not_applicable');

ALTER TABLE company_essential8_audit 
MODIFY COLUMN new_status ENUM('not_started', 'in_progress', 'compliant', 'non_compliant', 'not_applicable');

-- Source: 124_bc3_bcp_data_model.sql
CREATE TABLE IF NOT EXISTS bc_template (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  version VARCHAR(50) NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  schema_json JSON COMMENT 'Section and field definitions as JSON',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_bc_template_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_section_definition (
  id INT AUTO_INCREMENT PRIMARY KEY,
  template_id INT NOT NULL,
  `key` VARCHAR(100) NOT NULL COMMENT 'Unique section key within template',
  title VARCHAR(255) NOT NULL,
  order_index INT NOT NULL DEFAULT 0,
  schema_json JSON COMMENT 'Field definitions for this section',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (template_id) REFERENCES bc_template(id) ON DELETE CASCADE,
  INDEX idx_bc_section_template (template_id),
  INDEX idx_bc_section_template_order (template_id, order_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_plan_version (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  version_number INT NOT NULL,
  status ENUM('active', 'superseded') NOT NULL DEFAULT 'active',
  authored_by_user_id INT NOT NULL,
  authored_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  summary_change_note TEXT,
  content_json JSON COMMENT 'Section data as JSON',
  docx_export_hash VARCHAR(64),
  pdf_export_hash VARCHAR(64),
  INDEX idx_bc_plan_version_plan (plan_id),
  INDEX idx_bc_plan_version_plan_status (plan_id, status),
  INDEX idx_bc_plan_version_authored (authored_by_user_id),
  CONSTRAINT ck_version_number_positive CHECK (version_number > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  org_id INT COMMENT 'For multi-tenant support',
  title VARCHAR(255) NOT NULL,
  status ENUM('draft', 'in_review', 'approved', 'archived') NOT NULL DEFAULT 'draft',
  template_id INT,
  current_version_id INT,
  owner_user_id INT NOT NULL,
  approved_at_utc DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (template_id) REFERENCES bc_template(id) ON DELETE SET NULL,
  FOREIGN KEY (current_version_id) REFERENCES bc_plan_version(id) ON DELETE SET NULL,
  INDEX idx_bc_plan_org_status (org_id, status),
  INDEX idx_bc_plan_status_updated (status, updated_at),
  INDEX idx_bc_plan_template (template_id),
  INDEX idx_bc_plan_owner (owner_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE bc_plan_version 
  ADD CONSTRAINT fk_bc_plan_version_plan 
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS bc_contact (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  role VARCHAR(255),
  phone VARCHAR(50),
  email VARCHAR(255),
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_contact_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_process (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  rto_minutes INT COMMENT 'Recovery Time Objective in minutes',
  rpo_minutes INT COMMENT 'Recovery Point Objective in minutes',
  mtpd_minutes INT COMMENT 'Maximum Tolerable Period of Disruption in minutes',
  impact_rating VARCHAR(50) COMMENT 'e.g., critical, high, medium, low',
  dependencies_json JSON COMMENT 'Process dependencies as JSON',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_process_plan (plan_id),
  INDEX idx_bc_process_impact (impact_rating),
  CONSTRAINT ck_rto_non_negative CHECK (rto_minutes >= 0 OR rto_minutes IS NULL),
  CONSTRAINT ck_rpo_non_negative CHECK (rpo_minutes >= 0 OR rpo_minutes IS NULL),
  CONSTRAINT ck_mtpd_non_negative CHECK (mtpd_minutes >= 0 OR mtpd_minutes IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_risk (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  threat VARCHAR(500) NOT NULL,
  likelihood VARCHAR(50) COMMENT 'e.g., rare, unlikely, possible, likely, almost_certain',
  impact VARCHAR(50) COMMENT 'e.g., insignificant, minor, moderate, major, catastrophic',
  rating VARCHAR(50) COMMENT 'Overall risk rating, e.g., low, medium, high, critical',
  mitigation TEXT,
  owner_user_id INT COMMENT 'Risk owner',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_risk_plan (plan_id),
  INDEX idx_bc_risk_rating (rating),
  INDEX idx_bc_risk_owner (owner_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_attachment (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL COMMENT 'Path in storage system',
  content_type VARCHAR(100),
  size_bytes INT,
  uploaded_by_user_id INT NOT NULL,
  uploaded_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hash VARCHAR(64) COMMENT 'SHA256 hash for integrity verification',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_attachment_plan (plan_id),
  INDEX idx_bc_attachment_uploaded_by (uploaded_by_user_id),
  CONSTRAINT ck_size_non_negative CHECK (size_bytes >= 0 OR size_bytes IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_review (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  requested_by_user_id INT NOT NULL,
  reviewer_user_id INT NOT NULL,
  status ENUM('pending', 'approved', 'changes_requested') NOT NULL DEFAULT 'pending',
  requested_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  decided_at_utc DATETIME,
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_review_plan (plan_id),
  INDEX idx_bc_review_reviewer (reviewer_user_id),
  INDEX idx_bc_review_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_ack (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  user_id INT NOT NULL,
  ack_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ack_version_number INT COMMENT 'Version number acknowledged',
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_ack_plan (plan_id),
  INDEX idx_bc_ack_user (user_id),
  INDEX idx_bc_ack_plan_user (plan_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  action VARCHAR(100) NOT NULL COMMENT 'e.g., created, updated, approved, archived',
  actor_user_id INT NOT NULL,
  details_json JSON COMMENT 'Additional audit details as JSON',
  at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_audit_plan (plan_id),
  INDEX idx_bc_audit_actor (actor_user_id),
  INDEX idx_bc_audit_action (action),
  INDEX idx_bc_audit_at (at_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bc_change_log_map (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  change_guid VARCHAR(36) NOT NULL COMMENT 'GUID referencing change log file',
  imported_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_change_log_plan (plan_id),
  INDEX idx_bc_change_log_guid (change_guid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 125_bc11_vendors_table.sql
CREATE TABLE IF NOT EXISTS bc_vendor (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  vendor_type VARCHAR(100) COMMENT 'e.g., IT Service Provider, Supplier, Cloud Provider, etc.',
  contact_name VARCHAR(255),
  contact_email VARCHAR(255),
  contact_phone VARCHAR(50),
  sla_notes TEXT COMMENT 'Service Level Agreement details and notes',
  contract_reference VARCHAR(255) COMMENT 'Contract number or reference',
  criticality VARCHAR(50) COMMENT 'e.g., critical, high, medium, low',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bc_plan(id) ON DELETE CASCADE,
  INDEX idx_bc_vendor_plan (plan_id),
  INDEX idx_bc_vendor_criticality (criticality)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 126_bc02_bcp_data_model.sql
CREATE TABLE IF NOT EXISTS bcp_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL COMMENT 'Multi-tenant: company this plan belongs to',
  title VARCHAR(255) NOT NULL,
  executive_summary TEXT,
  objectives TEXT COMMENT 'Plan objectives and goals',
  version VARCHAR(50) COMMENT 'Plan version number',
  last_reviewed_at DATETIME COMMENT 'Last review date',
  next_review_at DATETIME COMMENT 'Next scheduled review date',
  distribution_notes TEXT COMMENT 'Notes about plan distribution',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_bcp_plan_company (company_id),
  INDEX idx_bcp_plan_next_review (next_review_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_distribution_entry (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  copy_number INT NOT NULL COMMENT 'Sequential copy number',
  name VARCHAR(255) NOT NULL COMMENT 'Recipient name',
  location VARCHAR(255) COMMENT 'Storage location of copy',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_distribution_plan (plan_id),
  INDEX idx_bcp_distribution_copy (plan_id, copy_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_risk (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  description TEXT NOT NULL,
  likelihood INT COMMENT 'Likelihood rating 1-4',
  impact INT COMMENT 'Impact rating 1-4',
  rating INT COMMENT 'Computed risk rating (likelihood × impact)',
  severity VARCHAR(50) COMMENT 'Computed severity: Low, Medium, High, Extreme (denormalized)',
  preventative_actions TEXT COMMENT 'Actions to prevent risk',
  contingency_plans TEXT COMMENT 'Plans if risk materializes',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_risk_plan (plan_id),
  INDEX idx_bcp_risk_severity (severity),
  CONSTRAINT ck_likelihood_range CHECK (likelihood >= 1 AND likelihood <= 4 OR likelihood IS NULL),
  CONSTRAINT ck_impact_range CHECK (impact >= 1 AND impact <= 4 OR impact IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_insurance_policy (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  type VARCHAR(100) NOT NULL COMMENT 'Policy type (e.g., Property, Liability)',
  coverage TEXT COMMENT 'What is covered',
  exclusions TEXT COMMENT 'What is excluded',
  insurer VARCHAR(255) COMMENT 'Insurance company name',
  contact VARCHAR(255) COMMENT 'Contact information',
  last_review_date DATETIME COMMENT 'Last policy review date',
  payment_terms VARCHAR(255) COMMENT 'Payment schedule and terms',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_insurance_plan (plan_id),
  INDEX idx_bcp_insurance_review (last_review_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_backup_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  data_scope VARCHAR(255) NOT NULL COMMENT 'What data is backed up',
  frequency VARCHAR(100) COMMENT 'Backup frequency (e.g., Daily, Weekly)',
  medium VARCHAR(100) COMMENT 'Backup medium (e.g., Cloud, Tape)',
  owner VARCHAR(255) COMMENT 'Person/team responsible',
  steps TEXT COMMENT 'Backup procedure steps',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_backup_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_critical_activity (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  priority ENUM('High', 'Medium', 'Low') COMMENT 'Activity priority',
  supplier_dependency ENUM('None', 'Sole', 'Major', 'Many') COMMENT 'Level of supplier dependency',
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_critical_activity_plan (plan_id),
  INDEX idx_bcp_critical_activity_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_impact (
  id INT AUTO_INCREMENT PRIMARY KEY,
  critical_activity_id INT NOT NULL,
  losses_financial TEXT COMMENT 'Financial impact description',
  losses_staffing TEXT COMMENT 'Staffing impact description',
  losses_reputation TEXT COMMENT 'Reputational impact description',
  fines TEXT COMMENT 'Potential fines and penalties',
  legal_liability TEXT COMMENT 'Legal liability description',
  rto_hours INT COMMENT 'Recovery Time Objective in hours',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (critical_activity_id) REFERENCES bcp_critical_activity(id) ON DELETE CASCADE,
  INDEX idx_bcp_impact_activity (critical_activity_id),
  INDEX idx_bcp_impact_rto (rto_hours),
  CONSTRAINT ck_rto_positive CHECK (rto_hours >= 0 OR rto_hours IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_checklist_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  phase ENUM('Immediate', 'CrisisRecovery') NOT NULL COMMENT 'Response phase',
  label VARCHAR(500) NOT NULL,
  default_order INT NOT NULL DEFAULT 0 COMMENT 'Display order',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_checklist_plan (plan_id),
  INDEX idx_bcp_checklist_phase (phase),
  INDEX idx_bcp_checklist_order (plan_id, phase, default_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_checklist_tick (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  checklist_item_id INT NOT NULL,
  incident_id INT NOT NULL,
  is_done BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Completion status',
  done_at DATETIME COMMENT 'When completed',
  done_by INT COMMENT 'User ID who completed',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  FOREIGN KEY (checklist_item_id) REFERENCES bcp_checklist_item(id) ON DELETE CASCADE,
  FOREIGN KEY (incident_id) REFERENCES bcp_incident(id) ON DELETE CASCADE,
  INDEX idx_bcp_tick_incident (incident_id),
  INDEX idx_bcp_tick_item (checklist_item_id),
  INDEX idx_bcp_tick_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_evacuation_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  meeting_point VARCHAR(500) COMMENT 'Primary meeting point location',
  floorplan_file_id INT COMMENT 'Reference to uploaded floorplan file',
  notes TEXT COMMENT 'Additional evacuation notes',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_evacuation_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_emergency_kit_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  category ENUM('Document', 'Equipment') NOT NULL COMMENT 'Item category',
  name VARCHAR(255) NOT NULL,
  notes TEXT,
  last_checked_at DATETIME COMMENT 'Last verification date',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_kit_plan (plan_id),
  INDEX idx_bcp_kit_category (category),
  INDEX idx_bcp_kit_checked (last_checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_role (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  responsibilities TEXT COMMENT 'Role responsibilities',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_role_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_role_assignment (
  id INT AUTO_INCREMENT PRIMARY KEY,
  role_id INT NOT NULL,
  user_id INT NOT NULL COMMENT 'Assigned user',
  is_alternate BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Is this an alternate/backup?',
  contact_info VARCHAR(500) COMMENT 'Emergency contact information',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (role_id) REFERENCES bcp_role(id) ON DELETE CASCADE,
  INDEX idx_bcp_role_assignment_role (role_id),
  INDEX idx_bcp_role_assignment_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_contact (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  kind ENUM('Internal', 'External') NOT NULL COMMENT 'Contact type',
  person_or_org VARCHAR(255) NOT NULL COMMENT 'Name of person or organization',
  phones VARCHAR(500) COMMENT 'Phone numbers (comma-separated)',
  email VARCHAR(255),
  responsibility_or_agency VARCHAR(500) COMMENT 'Role/responsibility or agency name',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_contact_plan (plan_id),
  INDEX idx_bcp_contact_kind (kind)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_event_log_entry (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  incident_id INT,
  happened_at DATETIME NOT NULL COMMENT 'Event timestamp',
  author_id INT COMMENT 'User who logged this event',
  notes TEXT NOT NULL,
  initials VARCHAR(10) COMMENT 'Author initials for quick reference',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  FOREIGN KEY (incident_id) REFERENCES bcp_incident(id) ON DELETE CASCADE,
  INDEX idx_bcp_event_plan (plan_id),
  INDEX idx_bcp_event_incident (incident_id),
  INDEX idx_bcp_event_time (happened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_recovery_action (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  critical_activity_id INT,
  action TEXT NOT NULL,
  resources TEXT COMMENT 'Required resources',
  owner_id INT COMMENT 'User responsible for action',
  rto_hours INT COMMENT 'Recovery time objective in hours',
  due_date DATETIME COMMENT 'Target completion date',
  completed_at DATETIME COMMENT 'Actual completion date',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  FOREIGN KEY (critical_activity_id) REFERENCES bcp_critical_activity(id) ON DELETE SET NULL,
  INDEX idx_bcp_recovery_plan (plan_id),
  INDEX idx_bcp_recovery_activity (critical_activity_id),
  INDEX idx_bcp_recovery_owner (owner_id),
  INDEX idx_bcp_recovery_due (due_date),
  CONSTRAINT ck_recovery_rto_positive CHECK (rto_hours >= 0 OR rto_hours IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_recovery_contact (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  org_name VARCHAR(255) NOT NULL COMMENT 'Organization name',
  contact_name VARCHAR(255) COMMENT 'Contact person name',
  title VARCHAR(255) COMMENT 'Contact person title',
  phone VARCHAR(50),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_recovery_contact_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_insurance_claim (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  insurer VARCHAR(255) NOT NULL,
  claim_date DATETIME COMMENT 'Date claim was filed',
  details TEXT COMMENT 'Claim details',
  follow_up_actions TEXT COMMENT 'Follow-up actions needed',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_claim_plan (plan_id),
  INDEX idx_bcp_claim_date (claim_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_market_change (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  `change` TEXT NOT NULL COMMENT 'Description of market change',
  impact TEXT COMMENT 'Impact on business continuity',
  options TEXT COMMENT 'Response options',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_market_plan (plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_training_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  training_date DATETIME NOT NULL COMMENT 'Training session date',
  training_type VARCHAR(255) COMMENT 'Type of training (e.g., Tabletop, Full-scale)',
  comments TEXT COMMENT 'Training notes and outcomes',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_training_plan (plan_id),
  INDEX idx_bcp_training_date (training_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_review_item (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  review_date DATETIME NOT NULL COMMENT 'Date of review',
  reason TEXT COMMENT 'Reason for review',
  changes_made TEXT COMMENT 'Summary of changes made',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (plan_id) REFERENCES bcp_plan(id) ON DELETE CASCADE,
  INDEX idx_bcp_review_plan (plan_id),
  INDEX idx_bcp_review_date (review_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 126_bcp_plan_overview.sql
CREATE TABLE IF NOT EXISTS bcp_plan_overview (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT 'Business Continuity Plan',
    executive_summary TEXT,
    version VARCHAR(50) DEFAULT '1.0',
    last_reviewed DATETIME,
    next_review DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_company_plan (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_objectives (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id INT NOT NULL,
    objective_text TEXT NOT NULL,
    display_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES bcp_plan_overview(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_distribution_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id INT NOT NULL,
    copy_number VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES bcp_plan_overview(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE roles
ADD COLUMN IF NOT EXISTS bcp_view BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE roles
ADD COLUMN IF NOT EXISTS bcp_edit BOOLEAN NOT NULL DEFAULT FALSE;

-- Source: 127_bc05_bia_enhancements.sql
ALTER TABLE bcp_critical_activity 
ADD COLUMN IF NOT EXISTS importance INT COMMENT 'Importance rating 1-5 (1=most important)';

CREATE INDEX idx_bcp_critical_activity_importance 
ON bcp_critical_activity(importance);

ALTER TABLE bcp_critical_activity 
ADD CONSTRAINT IF NOT EXISTS ck_importance_range 
CHECK (importance >= 1 AND importance <= 5 OR importance IS NULL);

ALTER TABLE bcp_impact 
ADD COLUMN IF NOT EXISTS losses_increased_costs TEXT COMMENT 'Increased costs impact description';

ALTER TABLE bcp_impact 
ADD COLUMN IF NOT EXISTS losses_product_service TEXT COMMENT 'Product/service delivery impact description';

ALTER TABLE bcp_impact 
ADD COLUMN IF NOT EXISTS losses_comments TEXT COMMENT 'Additional comments on losses and impacts';

-- Source: 128_ticket_watchers_email_support.sql
ALTER TABLE ticket_watchers
ADD COLUMN IF NOT EXISTS email VARCHAR(255) NULL AFTER user_id;

ALTER TABLE ticket_watchers 
MODIFY COLUMN user_id INT NULL;

CREATE INDEX idx_ticket_watchers_ticket_id
    ON ticket_watchers (ticket_id);

CREATE INDEX idx_ticket_watchers_user_id
    ON ticket_watchers (user_id);

ALTER TABLE ticket_watchers
DROP INDEX IF EXISTS uq_ticket_watchers_ticket_user;

CREATE UNIQUE INDEX uq_ticket_watchers_ticket_user
    ON ticket_watchers (ticket_id, user_id);

CREATE UNIQUE INDEX uq_ticket_watchers_ticket_email
    ON ticket_watchers (ticket_id, email(191));

ALTER TABLE ticket_watchers
ADD CONSTRAINT chk_ticket_watchers_identity
CHECK (user_id IS NOT NULL OR email IS NOT NULL);

-- Source: 129_ticket_attachments.sql
CREATE TABLE IF NOT EXISTS ticket_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT UNSIGNED NOT NULL,
    mime_type VARCHAR(127) NULL,
    access_level VARCHAR(32) NOT NULL DEFAULT 'closed',
    uploaded_by_user_id INT NULL,
    uploaded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_ticket_attachments_ticket_id (ticket_id),
    INDEX idx_ticket_attachments_uploaded_by (uploaded_by_user_id),
    INDEX idx_ticket_attachments_access_level (access_level),
    CONSTRAINT fk_ticket_attachments_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_attachments_uploader FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT chk_ticket_attachments_access_level CHECK (access_level IN ('open', 'closed', 'restricted'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 131_labour_type_rates.sql
ALTER TABLE ticket_labour_types
    ADD COLUMN IF NOT EXISTS rate DECIMAL(10,2) NULL AFTER name;

-- Source: 134_ticket_status_default.sql
ALTER TABLE ticket_statuses 
ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NOT NULL DEFAULT 0 AFTER public_status;

CREATE INDEX idx_ticket_statuses_default ON ticket_statuses (is_default);

-- Source: 137_knowledge_base_section_companies.sql
CREATE TABLE IF NOT EXISTS knowledge_base_section_companies (
    section_id INT NOT NULL,
    company_id INT NOT NULL,
    PRIMARY KEY (section_id, company_id),
    CONSTRAINT fk_kb_section_companies_section FOREIGN KEY (section_id) REFERENCES knowledge_base_sections(id) ON DELETE CASCADE,
    CONSTRAINT fk_kb_section_companies_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_kb_section_companies_section ON knowledge_base_section_companies (section_id);

CREATE INDEX idx_kb_section_companies_company ON knowledge_base_section_companies (company_id);

-- Source: 138_user_specific_permissions.sql
CREATE TABLE IF NOT EXISTS user_permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  company_id INT NOT NULL,
  permission VARCHAR(100) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by INT NULL,
  UNIQUE KEY uq_user_permissions_user_company_permission (user_id, company_id, permission),
  CONSTRAINT fk_user_permissions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_permissions_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_permissions_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user_permissions_user_company (user_id, company_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 139_service_status_dashboard.sql
CREATE TABLE IF NOT EXISTS service_status_services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'operational',
  status_message TEXT NULL,
  display_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  updated_by INT NULL,
  CONSTRAINT fk_service_status_services_updated_by FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_service_status_services_status (status),
  INDEX idx_service_status_services_display_order (display_order)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_status_service_companies (
  service_id INT NOT NULL,
  company_id INT NOT NULL,
  PRIMARY KEY (service_id, company_id),
  CONSTRAINT fk_service_status_companies_service FOREIGN KEY (service_id) REFERENCES service_status_services(id) ON DELETE CASCADE,
  CONSTRAINT fk_service_status_companies_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  INDEX idx_service_status_companies_company (company_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 140_service_status_tags.sql
ALTER TABLE service_status_services 
ADD COLUMN IF NOT EXISTS tags TEXT NULL COMMENT 'Comma-separated tags generated by AI';

-- Source: 141_add_booking_link_to_users.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS booking_link_url VARCHAR(500);

-- Source: 141_email_tracking.sql
ALTER TABLE ticket_replies 
ADD COLUMN IF NOT EXISTS email_tracking_id VARCHAR(64) NULL COMMENT 'Unique tracking ID for email open tracking',
ADD COLUMN IF NOT EXISTS email_sent_at DATETIME(6) NULL COMMENT 'Timestamp when email was sent',
ADD COLUMN IF NOT EXISTS email_opened_at DATETIME(6) NULL COMMENT 'Timestamp of first email open',
ADD COLUMN IF NOT EXISTS email_open_count INT NOT NULL DEFAULT 0 COMMENT 'Number of times email was opened',
ADD INDEX idx_ticket_replies_tracking_id (email_tracking_id);

-- Source: 142_add_email_signature_to_users.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_signature TEXT;

-- Source: 143_smtp2go_tracking.sql
ALTER TABLE ticket_replies 
ADD COLUMN IF NOT EXISTS smtp2go_message_id VARCHAR(128) NULL COMMENT 'SMTP2Go message ID from API response',
ADD COLUMN IF NOT EXISTS email_delivered_at DATETIME(6) NULL COMMENT 'Timestamp when email was delivered',
ADD COLUMN IF NOT EXISTS email_bounced_at DATETIME(6) NULL COMMENT 'Timestamp when email bounced',
ADD INDEX IF NOT EXISTS idx_ticket_replies_smtp2go_message_id (smtp2go_message_id);

ALTER TABLE email_tracking_events
ADD COLUMN IF NOT EXISTS smtp2go_data TEXT NULL COMMENT 'Full SMTP2Go webhook data (JSON)';

ALTER TABLE email_tracking_events
MODIFY COLUMN event_type ENUM('open', 'click', 'delivered', 'bounce', 'spam') NOT NULL COMMENT 'Type of tracking event';

-- Source: 144_imap_sync_known_only.sql
ALTER TABLE imap_accounts
ADD COLUMN IF NOT EXISTS sync_known_only TINYINT(1) NOT NULL DEFAULT 0
AFTER mark_as_read;

-- Source: 145_webhook_direction_tracking.sql
ALTER TABLE webhook_events
  ADD COLUMN IF NOT EXISTS direction VARCHAR(20) NOT NULL DEFAULT 'outgoing';

ALTER TABLE webhook_events
  ADD COLUMN IF NOT EXISTS source_url VARCHAR(500) NULL;

CREATE INDEX idx_webhook_events_direction
  ON webhook_events (direction, status);

-- Source: 146_automation_one_time_scheduling.sql
ALTER TABLE automations 
ADD COLUMN IF NOT EXISTS scheduled_time DATETIME(6) NULL AFTER next_run_at;

ALTER TABLE automations 
ADD COLUMN IF NOT EXISTS run_once TINYINT(1) NOT NULL DEFAULT 0 AFTER scheduled_time;

CREATE INDEX idx_automations_scheduled_time ON automations(scheduled_time);

-- Source: 147_smtp2go_additional_event_types.sql
ALTER TABLE ticket_replies 
ADD COLUMN IF NOT EXISTS email_processed_at DATETIME(6) NULL COMMENT 'Timestamp when email was accepted by SMTP2Go',
ADD COLUMN IF NOT EXISTS email_rejected_at DATETIME(6) NULL COMMENT 'Timestamp when email was rejected';

ALTER TABLE email_tracking_events
MODIFY COLUMN event_type ENUM('open', 'click', 'delivered', 'bounce', 'spam', 'processed', 'rejected') NOT NULL COMMENT 'Type of tracking event';

-- Source: 148_shop_quotes.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_access_quotes TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_access_quotes TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 152_automation_execution_order.sql
ALTER TABLE automations ADD COLUMN IF NOT EXISTS execution_order INT NOT NULL DEFAULT 0 AFTER description;

CREATE INDEX idx_automations_execution_order ON automations(execution_order);

-- Source: 154_ticket_list_indexes.sql
CREATE INDEX idx_tickets_updated_at
    ON tickets (updated_at);

CREATE INDEX idx_tickets_status_updated_at
    ON tickets (status, updated_at);

CREATE INDEX idx_tickets_company_updated_at
    ON tickets (company_id, updated_at);

CREATE INDEX idx_tickets_assigned_user_updated_at
    ON tickets (assigned_user_id, updated_at);

CREATE INDEX idx_tickets_requester_updated_at
    ON tickets (requester_id, updated_at);

CREATE INDEX idx_ticket_watchers_user_ticket_id
    ON ticket_watchers (user_id, ticket_id);

-- Source: 155_user_sidebar_preferences.sql
CREATE TABLE IF NOT EXISTS user_sidebar_preferences (
  user_id INT NOT NULL,
  preferences_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_user_sidebar_preferences_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 159_csp_tenant_mapping.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS csp_tenant_id VARCHAR(64) DEFAULT NULL;

-- Source: 160_asset_custom_field_display_name.sql
ALTER TABLE asset_custom_field_definitions
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(255) NULL DEFAULT NULL AFTER name;

-- Source: 161_company_payment_method.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) NOT NULL DEFAULT 'invoice';

-- Source: 161_m365_credential_expiry.sql
ALTER TABLE company_m365_credentials
    ADD COLUMN IF NOT EXISTS app_object_id VARCHAR(255) NULL AFTER client_secret,
    ADD COLUMN IF NOT EXISTS client_secret_key_id VARCHAR(255) NULL AFTER app_object_id,
    ADD COLUMN IF NOT EXISTS client_secret_expires_at DATETIME NULL AFTER client_secret_key_id;

-- Source: 163_company_payment_method_rename.sql
ALTER TABLE companies MODIFY COLUMN payment_method VARCHAR(100) NOT NULL DEFAULT 'invoice_prepay';

-- Source: 164_cis_benchmark_results.sql
CREATE TABLE IF NOT EXISTS cis_benchmark_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    benchmark_category VARCHAR(100) NOT NULL,
    check_id VARCHAR(100) NOT NULL,
    check_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    details TEXT,
    run_at DATETIME NOT NULL,
    UNIQUE KEY uq_benchmark_check (company_id, benchmark_category, check_id),
    INDEX idx_benchmark_company (company_id),
    INDEX idx_benchmark_run_at (company_id, run_at),
    CONSTRAINT chk_benchmark_status CHECK (status IN ('pass', 'fail', 'unknown', 'not_applicable'))
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 165_cis_benchmark_exclusions.sql
CREATE TABLE IF NOT EXISTS cis_benchmark_exclusions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    check_id VARCHAR(100) NOT NULL,
    reason VARCHAR(500) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_benchmark_exclusion (company_id, check_id),
    INDEX idx_exclusion_company (company_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 167_company_require_po.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS require_po TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 169_staff_source.sql
ALTER TABLE staff ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'manual';

-- Source: 170_staff_m365_last_sign_in.sql
ALTER TABLE staff ADD COLUMN IF NOT EXISTS m365_last_sign_in DATETIME NULL;

-- Source: 172_staff_is_ex_staff.sql
ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS is_ex_staff TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 174_group_licenses.sql
CREATE TABLE IF NOT EXISTS group_licenses (
  group_id INT NOT NULL,
  license_id INT NOT NULL,
  PRIMARY KEY (group_id, license_id),
  FOREIGN KEY (group_id) REFERENCES office_groups(id) ON DELETE CASCADE,
  FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 178_license_sku_friendly_names.sql
CREATE TABLE IF NOT EXISTS license_sku_friendly_names (
  sku VARCHAR(255) NOT NULL,
  friendly_name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (sku)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 180_m365_per_company_admin_config.sql
ALTER TABLE company_m365_credentials
    ADD COLUMN IF NOT EXISTS admin_client_id VARCHAR(255) NULL AFTER client_secret_expires_at,
    ADD COLUMN IF NOT EXISTS admin_client_secret TEXT NULL AFTER admin_client_id,
    ADD COLUMN IF NOT EXISTS admin_tenant_id VARCHAR(255) NULL AFTER admin_client_secret,
    ADD COLUMN IF NOT EXISTS admin_app_object_id VARCHAR(255) NULL AFTER admin_tenant_id,
    ADD COLUMN IF NOT EXISTS admin_secret_key_id VARCHAR(255) NULL AFTER admin_app_object_id,
    ADD COLUMN IF NOT EXISTS admin_secret_expires_at DATETIME NULL AFTER admin_secret_key_id,
    ADD COLUMN IF NOT EXISTS pkce_client_id VARCHAR(255) NULL AFTER admin_secret_expires_at;

-- Source: 181_license_sku_mapping_hidden.sql
ALTER TABLE license_sku_friendly_names
  ADD COLUMN IF NOT EXISTS hidden TINYINT(1) NOT NULL DEFAULT 0 AFTER friendly_name;

-- Source: 181_staff_onboarding_workflows.sql
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS company_onboarding_workflow_id VARCHAR(128) NULL;

CREATE TABLE IF NOT EXISTS company_onboarding_workflow_policies (
    id INT NOT NULL AUTO_INCREMENT,
    company_id INT NOT NULL,
    workflow_key VARCHAR(128) NOT NULL DEFAULT 'staff_onboarding_m365',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    max_retries INT NOT NULL DEFAULT 2,
    config_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_company_onboarding_workflow_policies_company (company_id),
    CONSTRAINT fk_company_onboarding_workflow_policies_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS staff_onboarding_workflow_executions (
    id INT NOT NULL AUTO_INCREMENT,
    company_id INT NOT NULL,
    staff_id INT NOT NULL,
    workflow_key VARCHAR(128) NOT NULL DEFAULT 'staff_onboarding_m365',
    state VARCHAR(32) NOT NULL DEFAULT 'requested',
    current_step VARCHAR(128) NULL,
    retries_used INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    helpdesk_ticket_id INT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_staff_onboarding_workflow_executions_staff (staff_id),
    KEY idx_staff_onboarding_workflow_executions_company_state (company_id, state),
    CONSTRAINT fk_staff_onboarding_workflow_executions_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_workflow_executions_staff
        FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS staff_onboarding_workflow_step_logs (
    id INT NOT NULL AUTO_INCREMENT,
    execution_id INT NOT NULL,
    step_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempt INT NOT NULL DEFAULT 1,
    request_payload LONGTEXT NULL,
    response_payload LONGTEXT NULL,
    error_message TEXT NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_staff_onboarding_workflow_step_logs_execution (execution_id),
    CONSTRAINT fk_staff_onboarding_workflow_step_logs_execution
        FOREIGN KEY (execution_id) REFERENCES staff_onboarding_workflow_executions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 182_staff_intake_field_config.sql
CREATE TABLE IF NOT EXISTS staff_field_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field_key VARCHAR(100) NOT NULL UNIQUE,
    label VARCHAR(255) NOT NULL,
    field_type VARCHAR(20) NOT NULL,
    default_visible TINYINT(1) NOT NULL DEFAULT 1,
    default_required TINYINT(1) NOT NULL DEFAULT 0,
    default_sort_order INT NOT NULL DEFAULT 0,
    validation_metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_staff_field_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    field_definition_id INT NOT NULL,
    visible TINYINT(1) NULL,
    required TINYINT(1) NULL,
    sort_order INT NULL,
    validation_metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_company_staff_field_config (company_id, field_definition_id),
    CONSTRAINT fk_company_staff_field_configs_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_company_staff_field_configs_definition
        FOREIGN KEY (field_definition_id) REFERENCES staff_field_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_staff_field_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    field_definition_id INT NOT NULL,
    option_value VARCHAR(255) NOT NULL,
    option_label VARCHAR(255) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_company_field_option (company_id, field_definition_id, option_value),
    CONSTRAINT fk_company_staff_field_options_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_company_staff_field_options_definition
        FOREIGN KEY (field_definition_id) REFERENCES staff_field_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 183_staff_custom_fields.sql
CREATE TABLE IF NOT EXISTS staff_custom_field_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NULL,
    base_definition_id INT NULL,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NULL,
    field_type ENUM('text', 'checkbox', 'date', 'select') NOT NULL DEFAULT 'text',
    display_order INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_staff_custom_field_name_per_company (company_id, name),
    KEY idx_staff_custom_field_base (base_definition_id),
    CONSTRAINT fk_staff_custom_field_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_custom_field_base
        FOREIGN KEY (base_definition_id) REFERENCES staff_custom_field_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS staff_custom_field_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field_definition_id INT NOT NULL,
    option_value VARCHAR(255) NOT NULL,
    option_label VARCHAR(255) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_staff_custom_field_option (field_definition_id, option_value),
    CONSTRAINT fk_staff_custom_field_options_definition
        FOREIGN KEY (field_definition_id) REFERENCES staff_custom_field_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS staff_custom_field_values (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_id INT NOT NULL,
    field_definition_id INT NOT NULL,
    value_text TEXT NULL,
    value_date DATE NULL,
    value_boolean TINYINT(1) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_staff_custom_field_value (staff_id, field_definition_id),
    CONSTRAINT fk_staff_custom_field_values_staff
        FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_custom_field_values_definition
        FOREIGN KEY (field_definition_id) REFERENCES staff_custom_field_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 184_unified_staff_fields.sql
ALTER TABLE company_staff_field_configs
ADD COLUMN IF NOT EXISTS field_type VARCHAR(20) NULL;

ALTER TABLE staff
MODIFY COLUMN email VARCHAR(255) NULL;

-- Source: 186_staff_custom_field_conditionals.sql
ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS condition_parent_name VARCHAR(100) NULL AFTER is_active,
    ADD COLUMN IF NOT EXISTS condition_operator ENUM('equals', 'not_equals', 'is_checked', 'is_not_checked') NULL AFTER condition_parent_name,
    ADD COLUMN IF NOT EXISTS condition_value VARCHAR(255) NULL AFTER condition_operator;

-- Source: 187_staff_onboarding_lifecycle.sql
ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS onboarding_status VARCHAR(32) NOT NULL DEFAULT 'requested',
  ADD COLUMN IF NOT EXISTS onboarding_complete TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS onboarding_completed_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN IF NOT EXISTS updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

CREATE INDEX idx_staff_company_onboarding_status
  ON staff (company_id, onboarding_status);

CREATE INDEX idx_staff_company_onboarding_complete
  ON staff (company_id, onboarding_complete);

CREATE INDEX idx_staff_company_updated_id
  ON staff (company_id, updated_at, id);

CREATE INDEX idx_staff_company_created_id
  ON staff (company_id, created_at, id);

-- Source: 188_staff_request_approvals.sql
ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS approval_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS requested_by_user_id INT NULL,
  ADD COLUMN IF NOT EXISTS requested_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS approved_by_user_id INT NULL,
  ADD COLUMN IF NOT EXISTS approved_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS request_notes TEXT NULL,
  ADD COLUMN IF NOT EXISTS approval_notes TEXT NULL;

CREATE INDEX idx_staff_company_approval_status
  ON staff (company_id, approval_status);

CREATE INDEX idx_staff_requested_by
  ON staff (requested_by_user_id);

CREATE INDEX idx_staff_approved_by
  ON staff (approved_by_user_id);

-- Source: 189_staff_onboarding_external_confirmation.sql
CREATE TABLE IF NOT EXISTS staff_onboarding_external_checkpoints (
    id INT NOT NULL AUTO_INCREMENT,
    execution_id INT NOT NULL,
    company_id INT NOT NULL,
    staff_id INT NOT NULL,
    confirmation_token_hash CHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    source VARCHAR(128) NULL,
    callback_timestamp DATETIME NULL,
    proof_reference_id VARCHAR(255) NULL,
    payload_hash VARCHAR(128) NULL,
    callback_payload_json LONGTEXT NULL,
    confirmed_by_api_key_id INT NULL,
    confirmed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_staff_onboarding_external_checkpoints_execution (execution_id),
    KEY idx_staff_onboarding_external_checkpoints_scope (company_id, staff_id, status),
    KEY idx_staff_onboarding_external_checkpoints_token (confirmation_token_hash),
    CONSTRAINT fk_staff_onboarding_external_checkpoints_execution
        FOREIGN KEY (execution_id) REFERENCES staff_onboarding_workflow_executions(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_external_checkpoints_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_external_checkpoints_staff
        FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_external_checkpoints_api_key
        FOREIGN KEY (confirmed_by_api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 190_staff_onboarding_external_confirmation_idempotency.sql
CREATE TABLE IF NOT EXISTS staff_onboarding_external_confirmation_idempotency (
    id INT NOT NULL AUTO_INCREMENT,
    api_key_id INT NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    request_fingerprint CHAR(64) NOT NULL,
    company_id INT NOT NULL,
    staff_id INT NOT NULL,
    response_status INT NULL,
    response_payload_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_staff_onboarding_external_confirmation_idempotency_key (api_key_id, idempotency_key),
    KEY idx_staff_onboarding_external_confirmation_idempotency_scope (company_id, staff_id),
    CONSTRAINT fk_staff_onboarding_external_confirmation_idempotency_api_key
        FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_external_confirmation_idempotency_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_onboarding_external_confirmation_idempotency_staff
        FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 191_staff_onboarding_workflow_direction.sql
ALTER TABLE staff_onboarding_workflow_executions
    ADD COLUMN IF NOT EXISTS direction VARCHAR(32) NOT NULL DEFAULT 'onboarding' AFTER workflow_key;

CREATE INDEX idx_staff_onboarding_workflow_executions_direction_state
    ON staff_onboarding_workflow_executions (company_id, direction, state);

-- Source: 192_staff_workflow_scheduling.sql
ALTER TABLE staff_onboarding_workflow_executions
    ADD COLUMN IF NOT EXISTS scheduled_for_utc DATETIME NULL AFTER requested_at,
    ADD COLUMN IF NOT EXISTS requested_timezone VARCHAR(64) NULL AFTER scheduled_for_utc;

-- Source: 193_staff_custom_field_groups.sql
ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS field_group VARCHAR(120) NULL AFTER field_type;

-- Source: 194_staff_custom_field_condition_select_map.sql
ALTER TABLE staff_custom_field_definitions
    MODIFY COLUMN condition_operator ENUM('equals', 'not_equals', 'is_checked', 'is_not_checked', 'select_map') NULL;

-- Source: 195_staff_custom_field_help_text.sql
ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS help_text VARCHAR(500) NULL AFTER display_name;

-- Source: 196_staff_custom_field_condition_one_of.sql
ALTER TABLE staff_custom_field_definitions
    MODIFY COLUMN condition_operator ENUM('equals', 'not_equals', 'one_of', 'is_checked', 'is_not_checked', 'select_map') NULL;

-- Source: 197_staff_workflow_execution_history.sql
ALTER TABLE staff_onboarding_workflow_executions
    ADD INDEX idx_staff_onboarding_workflow_executions_staff (staff_id);

ALTER TABLE staff_onboarding_workflow_executions
    DROP INDEX uq_staff_onboarding_workflow_executions_staff;

-- Source: 198_service_status_ai_lookup.sql
ALTER TABLE service_status_services
    ADD COLUMN IF NOT EXISTS ai_lookup_enabled TINYINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ai_lookup_url VARCHAR(500) NULL,
    ADD COLUMN IF NOT EXISTS ai_lookup_prompt TEXT NULL,
    ADD COLUMN IF NOT EXISTS ai_lookup_model_override VARCHAR(200) NULL,
    ADD COLUMN IF NOT EXISTS ai_lookup_frequency_operational INT NOT NULL DEFAULT 60,
    ADD COLUMN IF NOT EXISTS ai_lookup_frequency_degraded INT NOT NULL DEFAULT 15,
    ADD COLUMN IF NOT EXISTS ai_lookup_frequency_partial_outage INT NOT NULL DEFAULT 10,
    ADD COLUMN IF NOT EXISTS ai_lookup_frequency_outage INT NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS ai_lookup_frequency_maintenance INT NOT NULL DEFAULT 60,
    ADD COLUMN IF NOT EXISTS ai_lookup_last_checked_at DATETIME NULL,
    ADD COLUMN IF NOT EXISTS ai_lookup_last_status VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS ai_lookup_last_message TEXT NULL;

-- Source: 199_kid_friendly_words.sql
CREATE TABLE IF NOT EXISTS workflow_kid_friendly_words (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    word  VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_workflow_kid_friendly_words_word (word)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 201_staff_workflow_policy_direction.sql
ALTER TABLE company_onboarding_workflow_policies
    ADD COLUMN IF NOT EXISTS direction VARCHAR(32) NOT NULL DEFAULT 'onboarding' AFTER company_id;

ALTER TABLE company_onboarding_workflow_policies
    DROP FOREIGN KEY IF EXISTS fk_company_onboarding_workflow_policies_company;

CREATE UNIQUE INDEX uq_company_workflow_policy_company_dir
    ON company_onboarding_workflow_policies (company_id, direction);

ALTER TABLE company_onboarding_workflow_policies
    ADD CONSTRAINT fk_company_onboarding_workflow_policies_company
        FOREIGN KEY IF NOT EXISTS (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Source: 202_offboarding_request_fields.sql
ALTER TABLE staff
    ADD COLUMN IF NOT EXISTS offboarding_out_of_office TEXT NULL,
    ADD COLUMN IF NOT EXISTS offboarding_email_forward_to VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS offboarding_mailbox_grant_emails TEXT NULL;

ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS offboarding_email_forwarding_enabled TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 202_staff_requests_table.sql
CREATE TABLE IF NOT EXISTS staff_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    mobile_phone VARCHAR(50) NULL,
    date_onboarded DATETIME NULL,
    department VARCHAR(255) NULL,
    job_title VARCHAR(255) NULL,
    request_notes TEXT NULL,
    custom_fields_json TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    requested_by_user_id INT NULL,
    requested_at DATETIME NULL,
    approved_by_user_id INT NULL,
    approved_at DATETIME NULL,
    approval_notes TEXT NULL,
    staff_id INT NULL COMMENT 'Linked staff record created on approval',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_staff_requests_company_status
    ON staff_requests (company_id, status);

CREATE INDEX idx_staff_requests_requested_by
    ON staff_requests (requested_by_user_id);

CREATE INDEX idx_staff_requests_company_updated
    ON staff_requests (company_id, updated_at, id);

-- Source: 204_add_hudu_id_to_companies.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS hudu_id VARCHAR(255) DEFAULT NULL;

ALTER TABLE companies ADD KEY IF NOT EXISTS companies_hudu_id (hudu_id);

-- Source: 204_staff_workflow_multiple_policies.sql
ALTER TABLE company_onboarding_workflow_policies
    ADD COLUMN IF NOT EXISTS delay_type VARCHAR(20) NOT NULL DEFAULT 'scheduled' AFTER direction;

ALTER TABLE company_onboarding_workflow_policies
    ADD COLUMN IF NOT EXISTS workflow_name VARCHAR(255) NULL AFTER workflow_key;

ALTER TABLE company_onboarding_workflow_policies
    ADD COLUMN IF NOT EXISTS sort_order INT NOT NULL DEFAULT 0 AFTER workflow_name;

ALTER TABLE company_onboarding_workflow_policies
    DROP FOREIGN KEY IF EXISTS fk_company_onboarding_workflow_policies_company;

CREATE UNIQUE INDEX uq_company_workflow_policy_company_dir_key
    ON company_onboarding_workflow_policies (company_id, direction, workflow_key);

ALTER TABLE company_onboarding_workflow_policies
    ADD CONSTRAINT fk_company_onboarding_workflow_policies_company
        FOREIGN KEY IF NOT EXISTS (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Source: 205_add_is_active_to_users.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 206_expand_condition_value_to_text.sql
ALTER TABLE staff_custom_field_definitions
    MODIFY COLUMN condition_value TEXT NULL;

-- Source: 207_staff_custom_field_type_multiselect.sql
ALTER TABLE staff_custom_field_definitions
    MODIFY COLUMN field_type ENUM('text', 'checkbox', 'date', 'select', 'multiselect') NOT NULL DEFAULT 'text';

-- Source: 208_audit_logs_request_id_and_indexes.sql
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS request_id VARCHAR(64) NULL AFTER metadata;

CREATE INDEX idx_audit_logs_user_created_at
  ON audit_logs(user_id, created_at);

CREATE INDEX idx_audit_logs_action_created_at
  ON audit_logs(action, created_at);

CREATE INDEX idx_audit_logs_request_id
  ON audit_logs(request_id);

-- Source: 208_user_preferences.sql
CREATE TABLE IF NOT EXISTS user_preferences (
  user_id INT NOT NULL,
  preference_key VARCHAR(190) NOT NULL,
  preference_value JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, preference_key),
  CONSTRAINT fk_user_preferences_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 209_m365_best_practices.sql
CREATE TABLE IF NOT EXISTS m365_best_practice_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    check_id VARCHAR(100) NOT NULL,
    check_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    details TEXT,
    run_at DATETIME NOT NULL,
    CONSTRAINT chk_m365_bp_status CHECK (status IN ('pass', 'fail', 'unknown', 'not_applicable'))
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX uq_m365_bp_check
    ON m365_best_practice_results (company_id, check_id);

CREATE INDEX idx_m365_bp_company
    ON m365_best_practice_results (company_id);

CREATE INDEX idx_m365_bp_run_at
    ON m365_best_practice_results (company_id, run_at);

CREATE TABLE IF NOT EXISTS m365_best_practice_settings (
    check_id VARCHAR(100) NOT NULL PRIMARY KEY,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 210_add_m365_best_practices_permission.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_view_m365_best_practices TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_view_m365_best_practices TINYINT(1) DEFAULT 0 NOT NULL;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_view_m365_best_practices TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_view_m365_best_practices TINYINT(1) DEFAULT 0 NOT NULL;

-- Source: 212_compliance_checks.sql
CREATE TABLE IF NOT EXISTS compliance_check_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  is_system TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_category_code (code)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS compliance_checks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category_id INT NOT NULL,
  code VARCHAR(100) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  guidance TEXT,
  default_review_interval_days INT NOT NULL DEFAULT 365,
  default_evidence_required TINYINT(1) NOT NULL DEFAULT 0,
  is_predefined TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  created_by INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_check_code (code),
  FOREIGN KEY (category_id) REFERENCES compliance_check_categories(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_category_id (category_id),
  INDEX idx_is_active (is_active)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_compliance_check_assignments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  check_id INT NOT NULL,
  status ENUM('not_started','in_progress','compliant','non_compliant','not_applicable') NOT NULL DEFAULT 'not_started',
  review_interval_days INT,
  last_checked_at DATETIME,
  last_checked_by INT,
  next_review_at DATETIME,
  notes TEXT,
  evidence_summary TEXT,
  owner_user_id INT,
  archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (check_id) REFERENCES compliance_checks(id) ON DELETE CASCADE,
  FOREIGN KEY (last_checked_by) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
  UNIQUE KEY unique_company_check (company_id, check_id),
  INDEX idx_company_id (company_id),
  INDEX idx_status (status),
  INDEX idx_next_review_at (next_review_at),
  INDEX idx_archived (archived)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_compliance_check_evidence (
  id INT AUTO_INCREMENT PRIMARY KEY,
  assignment_id INT NOT NULL,
  evidence_type ENUM('text','url','file') NOT NULL DEFAULT 'text',
  title VARCHAR(255) NOT NULL,
  content TEXT,
  file_path VARCHAR(500),
  uploaded_by INT,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (assignment_id) REFERENCES company_compliance_check_assignments(id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_assignment_id (assignment_id)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_compliance_check_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  assignment_id INT NOT NULL,
  company_id INT NOT NULL,
  user_id INT,
  action VARCHAR(100) NOT NULL,
  old_status ENUM('not_started','in_progress','compliant','non_compliant','not_applicable'),
  new_status ENUM('not_started','in_progress','compliant','non_compliant','not_applicable'),
  old_last_checked_at DATETIME,
  new_last_checked_at DATETIME,
  change_summary TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (assignment_id) REFERENCES company_compliance_check_assignments(id) ON DELETE CASCADE,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_assignment_id (assignment_id),
  INDEX idx_company_id (company_id),
  INDEX idx_created_at (created_at)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 214_compliance_checks_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_view_compliance_checks TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_view_compliance_checks TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_manage_compliance_checks TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_manage_compliance_checks TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_view_compliance_checks TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_view_compliance_checks TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_manage_compliance_checks TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_manage_compliance_checks TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 215_m365_best_practices_remediation.sql
ALTER TABLE m365_best_practice_results
    ADD COLUMN IF NOT EXISTS remediation_status VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS remediated_at DATETIME NULL;

-- Source: 216_m365_best_practices_auto_remediate.sql
ALTER TABLE m365_best_practice_settings
    ADD COLUMN IF NOT EXISTS auto_remediate TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 217_add_matrix_user_id_to_users.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS matrix_user_id VARCHAR(255) NULL;

-- Source: 220_m365_best_practice_company_exclusions.sql
CREATE TABLE IF NOT EXISTS m365_best_practice_company_exclusions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    check_id VARCHAR(100) NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX uq_m365_bp_company_excl
    ON m365_best_practice_company_exclusions (company_id, check_id);

CREATE INDEX idx_m365_bp_excl_company
    ON m365_best_practice_company_exclusions (company_id);

-- Source: 221_new_role_permissions.sql
ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_view_m365_user_mailboxes TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_view_m365_user_mailboxes TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_view_m365_shared_mailboxes TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_view_m365_shared_mailboxes TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE user_companies
  ADD COLUMN IF NOT EXISTS can_access_chat TINYINT(1);

ALTER TABLE user_companies
  MODIFY can_access_chat TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_view_m365_user_mailboxes TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_view_m365_user_mailboxes TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_view_m365_shared_mailboxes TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_view_m365_shared_mailboxes TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_access_chat TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_access_chat TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 222_company_report_sections.sql
CREATE TABLE IF NOT EXISTS company_report_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    section_key VARCHAR(64) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_company_report_section (company_id, section_key),
    KEY idx_company_report_sections_company (company_id),
    CONSTRAINT fk_company_report_sections_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Source: 223_company_report_settings.sql
CREATE TABLE IF NOT EXISTS company_report_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    auto_hide_empty TINYINT(1) NOT NULL DEFAULT 1,
    section_order TEXT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_company_report_settings (company_id),
    CONSTRAINT fk_company_report_settings_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Source: 223_licenses_auto_renew.sql
ALTER TABLE licenses
  ADD COLUMN IF NOT EXISTS auto_renew TINYINT(1) NULL DEFAULT NULL;

-- Source: 224_company_report_sections_detailed.sql
ALTER TABLE company_report_sections
    ADD COLUMN IF NOT EXISTS detailed TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 226_license_usage_history.sql
CREATE TABLE IF NOT EXISTS license_usage_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id INT NOT NULL,
    count INT NOT NULL,
    allocated INT NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_license_usage_history_license_id (license_id),
    INDEX idx_license_usage_history_license_recorded (license_id, recorded_at),
    CONSTRAINT fk_license_usage_history_license
        FOREIGN KEY (license_id) REFERENCES licenses (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 227_demo_company.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_demo TINYINT(1) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS demo_seed_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  seeded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  removed_at DATETIME NULL,
  company_id INT NULL,
  seeded_by_user_id INT NULL,
  note VARCHAR(500) NULL,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
  FOREIGN KEY (seeded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 230_pdf_cover_image.sql
ALTER TABLE site_settings ADD COLUMN IF NOT EXISTS pdf_cover_image VARCHAR(500) DEFAULT NULL;

-- Source: 232_ticket_reply_email_recipients.sql
CREATE TABLE IF NOT EXISTS ticket_reply_email_recipients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_reply_id INT NOT NULL COMMENT 'References ticket_replies.id',
    recipient_email VARCHAR(320) NOT NULL COMMENT 'Normalised lowercase recipient email',
    recipient_role ENUM('to', 'cc', 'bcc') NOT NULL DEFAULT 'to' COMMENT 'Recipient role on the message',
    recipient_name VARCHAR(255) NULL COMMENT 'Display name when available',
    tracking_id VARCHAR(64) NULL COMMENT 'Internal email_tracking_id for this send',
    smtp2go_message_id VARCHAR(128) NULL COMMENT 'SMTP2Go message ID returned by API',
    email_sent_at DATETIME(6) NULL COMMENT 'When this recipient was sent (or processed)',
    email_processed_at DATETIME(6) NULL COMMENT 'SMTP2Go processed event timestamp',
    email_delivered_at DATETIME(6) NULL COMMENT 'Delivered event timestamp',
    email_opened_at DATETIME(6) NULL COMMENT 'First open timestamp',
    email_open_count INT NOT NULL DEFAULT 0 COMMENT 'Number of opens recorded',
    email_bounced_at DATETIME(6) NULL COMMENT 'Bounce event timestamp',
    email_rejected_at DATETIME(6) NULL COMMENT 'Rejected event timestamp',
    email_spam_at DATETIME(6) NULL COMMENT 'Spam complaint timestamp',
    last_event_at DATETIME(6) NULL COMMENT 'Timestamp of the most recent event',
    last_event_type VARCHAR(32) NULL COMMENT 'Most recent event type seen',
    last_event_detail TEXT NULL COMMENT 'Optional detail (e.g. bounce reason)',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_reply_recipients_reply (ticket_reply_id),
    INDEX idx_reply_recipients_tracking (tracking_id),
    INDEX idx_reply_recipients_smtp2go (smtp2go_message_id),
    INDEX idx_reply_recipients_recipient (recipient_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 235_tray_app.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS tray_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 235_trello_integration.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trello_board_id VARCHAR(255) NULL DEFAULT NULL;

-- Source: 236_tray_phase5.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS tray_notifications_enabled TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 237_trello_per_company_credentials.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trello_api_key VARCHAR(255) NULL DEFAULT NULL;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS trello_token VARCHAR(255) NULL DEFAULT NULL;

-- Source: 240_huntress_organization_id.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS huntress_organization_id VARCHAR(64) DEFAULT NULL;

ALTER TABLE companies ADD KEY IF NOT EXISTS companies_huntress_organization_id (huntress_organization_id);

-- Source: 242_m365_diagnostics.sql
CREATE TABLE IF NOT EXISTS m365_permission_check_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    app_id VARCHAR(100) NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    role_id VARCHAR(100) NOT NULL,
    role_name VARCHAR(255) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'unknown',
    checked_at DATETIME NOT NULL,
    CONSTRAINT chk_m365_perm_status CHECK (status IN ('pass', 'fail', 'unknown'))
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX uq_m365_perm_check
    ON m365_permission_check_results (company_id, app_id, role_id);

CREATE INDEX idx_m365_perm_company
    ON m365_permission_check_results (company_id);

-- Source: 243_m365_permission_status_not_supported.sql
CREATE UNIQUE INDEX uq_m365_perm_check
    ON m365_permission_check_results (company_id, app_id, role_id);

CREATE INDEX idx_m365_perm_company
    ON m365_permission_check_results (company_id);

-- Source: 244_m365_permission_check_results_fix_autoincrement.sql
ALTER TABLE m365_permission_check_results
    MODIFY COLUMN id INTEGER NOT NULL AUTO_INCREMENT;

-- Source: 246_reporting_queries.sql
CREATE TABLE IF NOT EXISTS reporting_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(120) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    sql_query LONGTEXT NOT NULL,
    is_system TINYINT(1) NOT NULL DEFAULT 0,
    created_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_reporting_queries_slug (slug),
    CONSTRAINT fk_reporting_queries_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reporting_query_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query_id INT NOT NULL,
    user_id INT NOT NULL,
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_reporting_query_user (query_id, user_id),
    KEY idx_reporting_query_perm_user (user_id),
    CONSTRAINT fk_reporting_query_perm_query
        FOREIGN KEY (query_id) REFERENCES reporting_queries(id) ON DELETE CASCADE,
    CONSTRAINT fk_reporting_query_perm_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Source: 248_singleton_jobs.sql
CREATE TABLE IF NOT EXISTS singleton_jobs (
    job_name VARCHAR(191) NOT NULL PRIMARY KEY,
    owner_id VARCHAR(191) NOT NULL,
    expires_at DATETIME NOT NULL COMMENT 'UTC',
    updated_at DATETIME NOT NULL COMMENT 'UTC'
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_singleton_jobs_expires
    ON singleton_jobs (expires_at);

-- Source: 251_knowledge_base_manual_ai_tags.sql
ALTER TABLE knowledge_base_articles
    ADD COLUMN IF NOT EXISTS manual_ai_tags JSON NULL AFTER excluded_ai_tags;

-- Source: 251_plugin_registry.sql
CREATE TABLE IF NOT EXISTS plugin_registry (
  slug VARCHAR(255) PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  installed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 253_notification_exclusions.sql
CREATE TABLE IF NOT EXISTS notification_exclusions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_type VARCHAR(150) NOT NULL,
    excluded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_exclusions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE KEY uq_notification_exclusions_user_event (user_id, event_type)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 254_notification_exclusions_message_pattern.sql
ALTER TABLE notification_exclusions
  ADD COLUMN IF NOT EXISTS message_pattern VARCHAR(500) NOT NULL DEFAULT '' AFTER event_type,
  DROP INDEX uq_notification_exclusions_user_event,
  ADD UNIQUE KEY uq_notification_exclusions_user_event_pattern (user_id, event_type, message_pattern(200));

-- Source: 260_company_chat_defaults.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS customer_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 263_pending_staff_quotes_access.sql
ALTER TABLE pending_staff_access
  ADD COLUMN IF NOT EXISTS can_access_quotes TINYINT(1);

ALTER TABLE pending_staff_access
  MODIFY can_access_quotes TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 266_ticket_requester_staff.sql
ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS requester_staff_id INT NULL AFTER requester_id;

CREATE INDEX idx_tickets_requester_staff_id
  ON tickets (requester_staff_id);

-- Source: 267_invitation_signup_templates.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at DATETIME NULL;

CREATE TABLE IF NOT EXISTS account_verification_tokens (
  token VARCHAR(64) PRIMARY KEY,
  user_id INT NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 268_add_user_last_login_at.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at DATETIME NULL;

CREATE INDEX idx_users_last_login_at ON users (last_login_at);

-- Source: 270_automation_history.sql
CREATE TABLE IF NOT EXISTS automation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    automation_id INT NOT NULL,
    automation_run_id INT NULL,
    occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    action_name VARCHAR(255) NOT NULL,
    action_module VARCHAR(64) NULL,
    ticket_id INT NULL,
    ticket_number VARCHAR(64) NULL,
    status VARCHAR(32) NOT NULL,
    previous_values JSON NULL,
    result_payload JSON NULL,
    error_message TEXT NULL,
    CONSTRAINT fk_automation_history_automation FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_automation_history_automation_time ON automation_history (automation_id, occurred_at);

CREATE INDEX idx_automation_history_ticket ON automation_history (ticket_id);

CREATE INDEX idx_automation_history_status ON automation_history (status);

-- Source: 270_staff_workflow_wait_for_webhook.sql
ALTER TABLE staff_onboarding_external_checkpoints
    ADD COLUMN IF NOT EXISTS webhook_public_id VARCHAR(96) NULL AFTER confirmation_token_hash,
    ADD COLUMN IF NOT EXISTS webhook_post_key_hash CHAR(64) NULL AFTER webhook_public_id;

CREATE INDEX idx_staff_onboarding_external_checkpoints_webhook
    ON staff_onboarding_external_checkpoints (webhook_public_id, status);

-- Source: 271_ticket_status_changed_at.sql
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS status_changed_at DATETIME(6) NULL AFTER status;

CREATE INDEX idx_tickets_status_changed_at
    ON tickets (status, status_changed_at);

-- Source: 274_company_onedrive_export_settings.sql
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS onedrive_export_site_id VARCHAR(512) NULL,
    ADD COLUMN IF NOT EXISTS onedrive_export_site_name VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS onedrive_export_drive_id VARCHAR(512) NULL;

-- Source: 275_webhook_event_metadata.sql
ALTER TABLE webhook_events
    ADD COLUMN IF NOT EXISTS metadata TEXT NULL;

-- Source: 276_staff_custom_field_visibility.sql
ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS visible_to_job_titles TEXT NULL AFTER condition_value;

ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS visible_to_requester_emails TEXT NULL AFTER visible_to_job_titles;

-- Source: 277_staff_custom_field_m365_sync.sql
ALTER TABLE staff_custom_field_definitions
    ADD COLUMN IF NOT EXISTS m365_upn VARCHAR(255) NULL AFTER visible_to_requester_emails;

ALTER TABLE staff_custom_field_options
    ADD COLUMN IF NOT EXISTS m365_upn VARCHAR(255) NULL AFTER option_label;

-- Source: 278_rag_index.sql
CREATE TABLE IF NOT EXISTS rag_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(191) NOT NULL,
    company_id INT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NULL,
    permission_scope_json LONGTEXT NULL,
    metadata_json LONGTEXT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_rag_document_source UNIQUE (source_type, source_id, embedding_model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rag_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text LONGTEXT NOT NULL,
    chunk_hash VARCHAR(64) NOT NULL,
    embedding_json LONGTEXT NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    token_count INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_rag_chunks_document FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT uq_rag_chunk_document_index UNIQUE (document_id, chunk_index, embedding_model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rag_index_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_type VARCHAR(64) NULL,
    source_id VARCHAR(191) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    message TEXT NULL,
    started_at DATETIME(6) NULL,
    finished_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_rag_documents_source ON rag_documents (source_type, source_id);

CREATE INDEX idx_rag_documents_company_active ON rag_documents (company_id, is_active);

CREATE INDEX idx_rag_documents_indexed_at ON rag_documents (indexed_at);

CREATE INDEX idx_rag_chunks_active_model ON rag_chunks (is_active, embedding_model);

CREATE INDEX idx_rag_chunks_hash ON rag_chunks (chunk_hash);

CREATE INDEX idx_rag_jobs_status_created ON rag_index_jobs (status, created_at);

CREATE INDEX idx_rag_jobs_source ON rag_index_jobs (source_type, source_id);

-- Source: 279_rag_relationship_engine.sql
CREATE TABLE IF NOT EXISTS rag_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_document_id INT NOT NULL,
    target_document_id INT NOT NULL,
    relationship_type VARCHAR(64) NOT NULL DEFAULT 'NOT_RELEVANT',
    match_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    relevance_score DECIMAL(5,4) NOT NULL DEFAULT 0,
    confidence DECIMAL(5,4) NOT NULL DEFAULT 0,
    reason TEXT NULL,
    supporting_excerpt TEXT NULL,
    evaluated_model VARCHAR(128) NULL,
    evaluated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    source_hash VARCHAR(64) NOT NULL,
    target_hash VARCHAR(64) NOT NULL,
    evaluation_duration_ms INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_rag_relationship_source FOREIGN KEY (source_document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT fk_rag_relationship_target FOREIGN KEY (target_document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT uq_rag_relationship_pair UNIQUE (source_document_id, target_document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rag_relationship_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_document_id INT NOT NULL,
    target_document_id INT NOT NULL,
    priority INT NOT NULL DEFAULT 1000,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    started_at DATETIME(6) NULL,
    completed_at DATETIME(6) NULL,
    last_error TEXT NULL,
    CONSTRAINT fk_rag_relationship_queue_source FOREIGN KEY (source_document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT fk_rag_relationship_queue_target FOREIGN KEY (target_document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    CONSTRAINT uq_rag_relationship_queue_pair_status UNIQUE (source_document_id, target_document_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_rag_relationships_source ON rag_relationships (source_document_id, match_status, relationship_type);

CREATE INDEX idx_rag_relationships_target ON rag_relationships (target_document_id, match_status, relationship_type);

CREATE INDEX idx_rag_relationships_hashes ON rag_relationships (source_hash, target_hash);

CREATE INDEX idx_rag_relationship_queue_status ON rag_relationship_queue (status, priority, created_at);

-- Source: 280_rag_controls_and_tasks.sql
CREATE TABLE IF NOT EXISTS rag_matching_state (
    `key` VARCHAR(64) NOT NULL PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 282_asset_machine_type.sql
ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS machine_type VARCHAR(50) DEFAULT NULL;

-- Source: 282_ticket_status_hide_from_technicians.sql
ALTER TABLE ticket_statuses
ADD COLUMN IF NOT EXISTS hide_from_technicians TINYINT(1) NOT NULL DEFAULT 0 AFTER is_default;

CREATE INDEX idx_ticket_statuses_hide_from_technicians ON ticket_statuses (hide_from_technicians);

-- Source: 283_ticket_status_hide_from_admins.sql
ALTER TABLE ticket_statuses
ADD COLUMN IF NOT EXISTS hide_from_admins TINYINT(1) NOT NULL DEFAULT 0 AFTER hide_from_technicians;

CREATE INDEX idx_ticket_statuses_hide_from_admins ON ticket_statuses (hide_from_admins);

-- Source: 285_next_ticket_number.sql
ALTER TABLE site_settings
  ADD COLUMN IF NOT EXISTS next_ticket_number INT NULL;

-- Source: 285_scheduled_task_calendar_visibility.sql
ALTER TABLE scheduled_tasks
  ADD COLUMN IF NOT EXISTS exclude_from_calendar TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 286_scheduled_task_module_lifecycle.sql
ALTER TABLE scheduled_tasks
  ADD COLUMN IF NOT EXISTS disabled_by_module VARCHAR(100) NULL;

CREATE INDEX idx_scheduled_tasks_disabled_by_module
  ON scheduled_tasks (disabled_by_module);

-- Source: 290_ticket_syncro_updated_at.sql
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS syncro_updated_at DATETIME(6) NULL;

CREATE INDEX idx_tickets_syncro_updated_at ON tickets(syncro_updated_at);

-- Source: 291_email_blocklist.sql
CREATE TABLE IF NOT EXISTS email_blocklist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    reason TEXT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'manual',
    last_event_type VARCHAR(64) NULL,
    last_event_payload TEXT NULL,
    created_by_user_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_email_blocklist_email ON email_blocklist (email);

CREATE INDEX idx_email_blocklist_source ON email_blocklist (source);

-- Source: 291_ticket_review_date.sql
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS review_date DATE NULL;

CREATE INDEX idx_tickets_review_date ON tickets(review_date);

-- Source: 294_expand_webhook_attempt_request_body.sql
ALTER TABLE webhook_event_attempts
  MODIFY COLUMN request_body LONGTEXT NULL;

ALTER TABLE webhook_event_attempts
  MODIFY COLUMN request_headers LONGTEXT NULL;

ALTER TABLE webhook_event_attempts
  MODIFY COLUMN response_headers LONGTEXT NULL;

-- Source: 295_expand_ticket_reply_body.sql
ALTER TABLE ticket_replies
  MODIFY COLUMN body LONGTEXT NOT NULL;

-- Source: 296_ticket_reply_author_snapshot.sql
ALTER TABLE ticket_replies
ADD COLUMN IF NOT EXISTS author_email VARCHAR(255) NULL AFTER author_id;

ALTER TABLE ticket_replies
ADD COLUMN IF NOT EXISTS author_display_name VARCHAR(255) NULL AFTER author_email;

CREATE INDEX idx_ticket_replies_author_email
    ON ticket_replies (author_email);

-- Source: 298_enable_company_chat_notification_defaults.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS customer_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS tray_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS tray_notifications_enabled TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE companies MODIFY COLUMN customer_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE companies MODIFY COLUMN tray_chat_enabled TINYINT(1) NOT NULL DEFAULT 1;

ALTER TABLE companies MODIFY COLUMN tray_notifications_enabled TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 299_ticket_shipment_watches.sql
CREATE TABLE IF NOT EXISTS ticket_shipment_watches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    tracking_url VARCHAR(500) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    consignment_id VARCHAR(128) NULL,
    poll_interval_seconds INT NOT NULL DEFAULT 900,
    last_snapshot_hash CHAR(64) NULL,
    last_snapshot_json LONGTEXT NULL,
    last_checked_at DATETIME(6) NULL,
    last_posted_update_at DATETIME(6) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_ticket_shipment_watches_ticket (ticket_id),
    INDEX idx_ticket_shipment_watches_active_checked (active, last_checked_at),
    INDEX idx_ticket_shipment_watches_provider_active (provider, active),
    CONSTRAINT fk_ticket_shipment_watches_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 300_ticket_shipment_watch_public_comments.sql
ALTER TABLE ticket_shipment_watches
    ADD COLUMN IF NOT EXISTS public_comments_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- Source: 301_company_default_ticket_reply_billable.sql
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS default_ticket_replies_billable TINYINT(1) NOT NULL DEFAULT 1;

-- Source: 301_ticket_canned_responses.sql
CREATE TABLE IF NOT EXISTS ticket_canned_responses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  created_by_user_id INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_ticket_canned_responses_title (title),
  CONSTRAINT fk_ticket_canned_responses_created_by FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 302_ticket_page_clocks.sql
CREATE TABLE IF NOT EXISTS ticket_page_clocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    user_id INT NOT NULL,
    started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    last_seen_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    ended_at DATETIME(6) NULL,
    INDEX idx_ticket_page_clocks_ticket_started (ticket_id, started_at),
    INDEX idx_ticket_page_clocks_user_open (user_id, ended_at),
    CONSTRAINT fk_ticket_page_clocks_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_page_clocks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 305_huntress_sat_account_id.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS huntress_sat_account_id VARCHAR(64) DEFAULT NULL;

ALTER TABLE companies ADD KEY IF NOT EXISTS companies_huntress_sat_account_id (huntress_sat_account_id);

-- Source: 307_add_company_phone.sql
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS phone VARCHAR(50) DEFAULT NULL AFTER address;

-- Source: 308_user_m365_contact_integrations.sql
CREATE TABLE IF NOT EXISTS user_m365_contact_integrations (
    
    user_id INT NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    account_email VARCHAR(320) NULL,
    refresh_token TEXT NOT NULL,
    access_token TEXT NULL,
    token_expires_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_m365_contacts_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 309_configurable_dashboards.sql
CREATE TABLE IF NOT EXISTS company_dashboard_layouts (
 company_id INT NOT NULL PRIMARY KEY, layout_json JSON NOT NULL, updated_by INT NOT NULL,
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 CONSTRAINT fk_dashboard_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
 CONSTRAINT fk_dashboard_updater FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 311_company_invoice_due_days.sql
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS invoice_due_days INT UNSIGNED NULL DEFAULT NULL AFTER xero_id;

-- Source: 312_ticket_attachment_blocklist.sql
CREATE TABLE IF NOT EXISTS ticket_attachment_blocklist (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sha256_hash CHAR(64) NOT NULL,
  original_filename VARCHAR(255) NULL,
  file_size BIGINT NULL,
  mime_type VARCHAR(255) NULL,
  created_by_user_id INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_ticket_attachment_blocklist_hash (sha256_hash),
  CONSTRAINT fk_ticket_attachment_blocklist_user
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 313_attachment_blocklist_thumbnails.sql
ALTER TABLE ticket_attachment_blocklist
  ADD COLUMN IF NOT EXISTS thumbnail_data MEDIUMBLOB NULL AFTER mime_type,
  ADD COLUMN IF NOT EXISTS thumbnail_mime_type VARCHAR(64) NULL AFTER thumbnail_data;

-- Source: 317_configurable_company_report_layout.sql
CREATE TABLE IF NOT EXISTS company_report_layouts (
    company_id INT NOT NULL PRIMARY KEY,
    layout_json LONGTEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_company_report_layout_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Source: 318_staff_requests_enabled.sql
ALTER TABLE staff_requests
    ADD COLUMN IF NOT EXISTS enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER department;

-- Source: 319_m365_direct_delivery.sql
ALTER TABLE ticket_reply_email_recipients
    ADD COLUMN IF NOT EXISTS m365_message_id VARCHAR(512) NULL COMMENT 'Graph message ID for a directly deposited message',
    ADD COLUMN IF NOT EXISTS m365_company_id INT NULL COMMENT 'Company whose M365 credentials own the mailbox',
    ADD INDEX IF NOT EXISTS idx_reply_recipients_m365_message (m365_message_id(191));

-- Source: 320_network_scanner.sql
ALTER TABLE assets ADD COLUMN IF NOT EXISTS mac_address VARCHAR(17) NULL;

-- Source: 322_asset_mac_addresses.sql
ALTER TABLE assets MODIFY COLUMN mac_address TEXT NULL;

-- Source: 324_network_device_alert_tickets.sql
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS network_device_ticket_alerts_enabled TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 328_windows_defender_management.sql
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS defender_enabled TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_scheduled_scan_type VARCHAR(16) NULL;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_scheduled_scan_day TINYINT NULL;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_scheduled_scan_time TIME NULL;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_auto_ticket_min_severity VARCHAR(16) NULL;

-- Source: 329_defender_automatic_ticket_options.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_auto_ticket_antivirus_off TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_auto_ticket_realtime_off TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_auto_ticket_tamper_off TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE companies ADD COLUMN IF NOT EXISTS defender_auto_ticket_threat_detected TINYINT(1) NOT NULL DEFAULT 0;

-- Source: 332_company_variables.sql
CREATE TABLE IF NOT EXISTS company_variable_definitions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_variable_values (
  company_id INT NOT NULL,
  variable_id INT NOT NULL,
  value TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (company_id, variable_id),
  CONSTRAINT fk_company_variable_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  CONSTRAINT fk_company_variable_definition FOREIGN KEY (variable_id) REFERENCES company_variable_definitions(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 342_service_level_agreements.sql
CREATE TABLE IF NOT EXISTS service_level_agreements (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    company_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    response_minutes INTEGER NOT NULL,
    resolution_minutes INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_sla_company (company_id),
    CONSTRAINT fk_sla_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_sla_events (
    ticket_id INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id, event_type),
    CONSTRAINT fk_ticket_sla_event_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 343_dmarc_reporting.sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS dmarc_reporting_code VARCHAR(32) NULL;

CREATE UNIQUE INDEX uq_companies_dmarc_reporting_code ON companies (dmarc_reporting_code);

-- Source: 343_priority_sla_templates.sql
CREATE TABLE IF NOT EXISTS sla_templates (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sla_template_targets (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    template_id INTEGER NOT NULL,
    priority VARCHAR(32) NOT NULL,
    response_minutes INTEGER NOT NULL,
    resolution_minutes INTEGER NOT NULL,
    UNIQUE KEY uq_sla_template_priority (template_id, priority),
    CONSTRAINT fk_sla_target_template FOREIGN KEY (template_id) REFERENCES sla_templates(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS company_sla_templates (
    company_id INTEGER NOT NULL PRIMARY KEY,
    template_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_company_sla_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_company_sla_template FOREIGN KEY (template_id) REFERENCES sla_templates(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 344_sla_pause_statuses.sql
CREATE TABLE IF NOT EXISTS sla_template_pause_statuses (
    template_id INTEGER NOT NULL,
    status VARCHAR(64) NOT NULL,
    PRIMARY KEY (template_id, status),
    CONSTRAINT fk_sla_pause_template FOREIGN KEY (template_id) REFERENCES sla_templates(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_status_history (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    ticket_id INTEGER NOT NULL,
    status VARCHAR(64) NOT NULL,
    started_at DATETIME NOT NULL,
    ended_at DATETIME NOT NULL,
    CONSTRAINT fk_ticket_status_history_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_ticket_status_history_ticket ON ticket_status_history (ticket_id, started_at);

-- Source: 345_normalize_ticket_sla_collations.sql
ALTER TABLE sla_template_targets
    MODIFY priority VARCHAR(32)
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

ALTER TABLE sla_template_pause_statuses
    MODIFY status VARCHAR(64)
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

ALTER TABLE ticket_status_history
    MODIFY status VARCHAR(64)
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;

-- Source: 347_ticket_suggested_assets.sql
CREATE TABLE IF NOT EXISTS ticket_suggested_assets (
  ticket_id INT NOT NULL,
  asset_id INT NOT NULL,
  matched_username VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (ticket_id, asset_id),
  CONSTRAINT ticket_suggested_assets_ticket_fk FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  CONSTRAINT ticket_suggested_assets_asset_fk FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 352_asset_boot_time.sql
ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS boot_time DATETIME DEFAULT NULL AFTER last_sync;

-- Source: 354_bcp_global_assessment_library.sql
CREATE TABLE IF NOT EXISTS bcp_global_risk (
  id INT AUTO_INCREMENT PRIMARY KEY,
  description TEXT NOT NULL,
  likelihood INT NOT NULL,
  impact INT NOT NULL,
  preventative_actions TEXT,
  contingency_plans TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_global_risk_likelihood CHECK (likelihood BETWEEN 1 AND 4),
  CONSTRAINT ck_global_risk_impact CHECK (impact BETWEEN 1 AND 4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_global_bia (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  priority ENUM('High', 'Medium', 'Low'),
  supplier_dependency ENUM('None', 'Sole', 'Major', 'Many'),
  importance INT,
  notes TEXT,
  losses_financial TEXT,
  losses_increased_costs TEXT,
  losses_staffing TEXT,
  losses_product_service TEXT,
  losses_reputation TEXT,
  fines TEXT,
  legal_liability TEXT,
  rto_hours INT,
  losses_comments TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_global_bia_importance CHECK (importance BETWEEN 1 AND 5 OR importance IS NULL),
  CONSTRAINT ck_global_bia_rto CHECK (rto_hours >= 0 OR rto_hours IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_global_risk_assignment (
  global_risk_id INT NOT NULL,
  company_id INT NOT NULL,
  risk_id INT NOT NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (global_risk_id, company_id),
  FOREIGN KEY (global_risk_id) REFERENCES bcp_global_risk(id) ON DELETE CASCADE,
  FOREIGN KEY (risk_id) REFERENCES bcp_risk(id) ON DELETE CASCADE,
  INDEX idx_global_risk_assignment_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bcp_global_bia_assignment (
  global_bia_id INT NOT NULL,
  company_id INT NOT NULL,
  critical_activity_id INT NOT NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (global_bia_id, company_id),
  FOREIGN KEY (global_bia_id) REFERENCES bcp_global_bia(id) ON DELETE CASCADE,
  FOREIGN KEY (critical_activity_id) REFERENCES bcp_critical_activity(id) ON DELETE CASCADE,
  INDEX idx_global_bia_assignment_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Source: 155_ticket_fulltext_search.sql
ALTER TABLE tickets ADD FULLTEXT INDEX idx_tickets_fulltext_search (subject, description, external_reference);
