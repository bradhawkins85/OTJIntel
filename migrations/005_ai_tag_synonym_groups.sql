-- Editable synonym groups used to match AI-generated terms to knowledge-base tags.
CREATE TABLE IF NOT EXISTS ai_tag_synonym_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  terms JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
