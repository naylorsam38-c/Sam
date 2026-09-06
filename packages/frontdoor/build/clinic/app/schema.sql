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

CREATE TABLE IF NOT EXISTS contacts (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [email] VARCHAR(255),
  [phone] VARCHAR(40),
  [type] ENUM,
  [payment_terms_days] INTEGER
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

CREATE TABLE IF NOT EXISTS invoices (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [contact] TEXT,
  [issue_date] DATE,
  [due_date] DATE,
  [reference] VARCHAR(255),
  [notes] TEXT,
  [sent_at] DATETIME,
  stage TEXT NOT NULL DEFAULT 'Draft'
);

CREATE TABLE IF NOT EXISTS invoice_lines (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [invoice] TEXT,
  [description] VARCHAR(255),
  [quantity] DECIMAL(18,4),
  [unit_amount] DECIMAL(18,2)
);

CREATE TABLE IF NOT EXISTS bills (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [contact] TEXT,
  [issue_date] DATE,
  [due_date] DATE,
  [amount] DECIMAL(18,2),
  [reference] VARCHAR(255),
  stage TEXT NOT NULL DEFAULT 'Draft'
);

CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [invoice] TEXT,
  [bill] TEXT,
  [amount] DECIMAL(18,2),
  [date] DATE,
  [method] ENUM
);
