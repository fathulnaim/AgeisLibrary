-- schema.sql
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS books;

CREATE TABLE users (
    username TEXT PRIMARY KEY, -- Limited to 30 chars in app.py
    email TEXT NOT NULL,         -- Used for OTP/MFA delivery
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL -- 'admin' or 'user'
);

CREATE TABLE books (
    book_id TEXT PRIMARY KEY, -- SCENARIO 3: Strictly 8 chars limit
    title TEXT NOT NULL,
    category TEXT NOT NULL,   -- Science, Math, etc.
    status TEXT NOT NULL,      -- 'Available' or 'Borrowed'
    borrowed_by TEXT
);