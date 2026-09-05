CREATE TABLE IF NOT EXISTS organisations (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [website] VARCHAR(2048),
  [phone] VARCHAR(40),
  [notes] TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [full_name] VARCHAR(255),
  [email] VARCHAR(255),
  [phone] VARCHAR(40),
  [organisation] TEXT
);

CREATE TABLE IF NOT EXISTS deals (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [title] VARCHAR(255),
  [value] DECIMAL(18,2),
  [owner] TEXT,
  [contact] TEXT,
  [organisation] TEXT,
  [expected_close_date] DATE,
  [lost_reason] ENUM,
  stage TEXT NOT NULL DEFAULT 'Lead in'
);

CREATE TABLE IF NOT EXISTS activitys (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [subject] VARCHAR(255),
  [type] ENUM,
  [due] DATETIME,
  [done] BOOLEAN,
  [owner] TEXT,
  [deal] TEXT
);
