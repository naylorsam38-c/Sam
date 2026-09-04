CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  name VARCHAR(255),
  description TEXT,
  owner TEXT,
  due_date DATE,
  colour ENUM
);
