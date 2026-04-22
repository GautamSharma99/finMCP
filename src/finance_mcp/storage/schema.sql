-- Personal Finance Analyst schema (PRD §4.1).
-- Keep this file as the authoritative DDL; cumulative migrations live in migrations/.

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    bank TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon TEXT,
    is_income BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE(name, parent_id)
);

CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'contains',
    category_id INTEGER NOT NULL REFERENCES categories(id),
    priority INTEGER NOT NULL DEFAULT 100,
    is_user_defined BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    txn_date DATE NOT NULL,
    value_date DATE,
    amount DECIMAL(12, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    raw_description TEXT NOT NULL,
    clean_merchant TEXT,
    category_id INTEGER REFERENCES categories(id),
    category_source TEXT,
    reference_no TEXT,
    running_balance DECIMAL(12, 2),
    is_transfer BOOLEAN NOT NULL DEFAULT 0,
    transfer_pair_id INTEGER REFERENCES transactions(id),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dedup_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_txn_merchant ON transactions(clean_merchant);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    period TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, period, start_date)
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    target_amount DECIMAL(12, 2) NOT NULL,
    current_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    deadline DATE,
    linked_account_id INTEGER REFERENCES accounts(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    rows_imported INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
