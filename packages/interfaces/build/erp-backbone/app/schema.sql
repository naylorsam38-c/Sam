CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [sku] VARCHAR(255),
  [sale_price] DECIMAL(18,2),
  [cost] DECIMAL(18,2),
  [stock_on_hand] INTEGER,
  [reorder_point] INTEGER
);

CREATE TABLE IF NOT EXISTS suppliers (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [email] VARCHAR(255),
  [phone] VARCHAR(40),
  [payment_terms] ENUM
);

CREATE TABLE IF NOT EXISTS customer_accounts (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [name] VARCHAR(255),
  [email] VARCHAR(255),
  [phone] VARCHAR(40),
  [delivery_address] TEXT
);

CREATE TABLE IF NOT EXISTS purchase_orders (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [supplier] TEXT,
  [order_date] DATE,
  [expected_date] DATE,
  [notes] TEXT,
  stage TEXT NOT NULL DEFAULT 'Draft'
);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [purchase_order] TEXT,
  [product] TEXT,
  [quantity] INTEGER,
  [unit_cost] DECIMAL(18,2)
);

CREATE TABLE IF NOT EXISTS sales_orders (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [customer_account] TEXT,
  [order_date] DATE,
  [notes] TEXT,
  stage TEXT NOT NULL DEFAULT 'Draft'
);

CREATE TABLE IF NOT EXISTS sales_order_lines (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [sales_order] TEXT,
  [product] TEXT,
  [quantity] INTEGER,
  [unit_price] DECIMAL(18,2)
);

CREATE TABLE IF NOT EXISTS stock_adjustments (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  [product] TEXT,
  [change] INTEGER,
  [reason] ENUM,
  [notes] TEXT
);
