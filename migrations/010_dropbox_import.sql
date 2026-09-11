CREATE TABLE IF NOT EXISTS dropbox_connections (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    app_key VARCHAR(255) NOT NULL,
    app_secret_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NULL,
    root_path VARCHAR(1024) NOT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT 1,
    account_email VARCHAR(320) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dropbox_imports (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    connection_id INTEGER NOT NULL,
    dropbox_folder_id VARCHAR(255) NOT NULL,
    dropbox_path VARCHAR(2048) NOT NULL,
    requester_email VARCHAR(320) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    ticket_id INTEGER NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (connection_id, dropbox_folder_id),
    FOREIGN KEY (connection_id) REFERENCES dropbox_connections(id) ON DELETE CASCADE,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE SET NULL
);
