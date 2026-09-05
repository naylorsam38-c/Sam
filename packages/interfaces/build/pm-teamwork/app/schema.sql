CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [description] TEXT,
  [owner] TEXT,
  [due_date] DATE,
  [colour] ENUM
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [title] VARCHAR(255),
  [description] TEXT,
  [assignee] TEXT,
  [due_date] DATE,
  [priority] ENUM,
  [project] TEXT,
  stage TEXT NOT NULL DEFAULT 'To do'
);

CREATE TABLE IF NOT EXISTS comments (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [body] TEXT,
  [task] TEXT
);
