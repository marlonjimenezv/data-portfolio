-- SQLite schema for the cleaned Online Retail II data.
DROP TABLE IF EXISTS invoice_lines;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY,
  country     TEXT NOT NULL
);

CREATE TABLE products (
  stock_code  TEXT PRIMARY KEY,
  description TEXT NOT NULL
);

CREATE TABLE invoices (
  invoice_no   TEXT PRIMARY KEY,
  invoice_date TEXT NOT NULL,              -- 'YYYY-MM-DD HH:MM:SS'
  month        TEXT NOT NULL,              -- 'YYYY-MM'
  type         TEXT NOT NULL CHECK (type IN ('Sale', 'Return')),
  customer_id  TEXT REFERENCES customers (customer_id),   -- NULL = guest checkout
  country      TEXT NOT NULL
);

CREATE TABLE invoice_lines (
  invoice_no   TEXT NOT NULL REFERENCES invoices (invoice_no),
  stock_code   TEXT NOT NULL REFERENCES products (stock_code),
  quantity     INTEGER NOT NULL,           -- negative for returns
  unit_price   REAL NOT NULL CHECK (unit_price > 0),
  line_revenue REAL NOT NULL
);

CREATE INDEX idx_lines_invoice ON invoice_lines (invoice_no);
CREATE INDEX idx_lines_product ON invoice_lines (stock_code);
CREATE INDEX idx_invoices_month ON invoices (month);
CREATE INDEX idx_invoices_customer ON invoices (customer_id);
