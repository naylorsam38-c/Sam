CREATE TABLE IF NOT EXISTS services (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [description] TEXT,
  [duration_minutes] INTEGER,
  [price] DECIMAL(18,2),
  [deposit_required] BOOLEAN,
  [deposit_amount] DECIMAL(18,2)
);

CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [full_name] VARCHAR(255),
  [email] VARCHAR(255),
  [phone] VARCHAR(40),
  [notes] TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [service] TEXT,
  [customer] TEXT,
  [staff_member] TEXT,
  [start] DATETIME,
  [notes] TEXT,
  [deposit_paid] BOOLEAN,
  stage TEXT NOT NULL DEFAULT 'Booked'
);
