# init_db_postgres.py

import os
import sys
import psycopg2

def get_env_var(name, default=None, required=True):
    value = os.environ.get(name, default)
    if required and value is None:
        print(f"❌ Environment variable '{name}' is not set.")
        sys.exit(1)
    return value

def init_db_postgres():
    # Use DATABASE_URL if set, otherwise use individual env vars
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=get_env_var('PGHOST', 'localhost', required=False),
            # CHANGE THIS LINE: Use a real database name, not "Local PostgreSQL"
            database=get_env_var('PGDATABASE', 'postgres', required=False),
            user=get_env_var('PGUSER', 'postgres', required=False),
            password=get_env_var('PGPASSWORD', '12Marks@255', required=False),
            port=os.environ.get('PGPORT', '5432')
        )
    cur = conn.cursor()

    # Users Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)

    # Ledger Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            head TEXT,
            ledger_page_no TEXT,
            opening_date TEXT
        );
    """)

    # Received Items Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS received_items (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            head TEXT,
            ledger_page_no TEXT,
            available_stock TEXT,
            qty INTEGER,
            price_unit TEXT,
            remarks TEXT,
            date TEXT
        );
    """)

    # Issued Items Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issued_items (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            head TEXT,
            ledger_page_no TEXT,
            available_stock INTEGER,
            qty INTEGER,
            issued_to TEXT,
            date TEXT,
            remarks TEXT
        );
    """)

    # Items Category Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items_category (
            id SERIAL PRIMARY KEY,
            category_name TEXT NOT NULL
        );
    """)

    # Head Office Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS head_office (
            id SERIAL PRIMARY KEY,
            head TEXT,
            office_name TEXT
        );
    """)

    # Ledger Entries Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            date TEXT,
            type TEXT,
            receive_from TEXT,
            issue_to TEXT,
            prev_bal INTEGER,
            receive_qty INTEGER,
            issue_qty INTEGER,
            balance INTEGER,
            remark TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ PostgreSQL database initialized successfully.")

if __name__ == "__main__":
    init_db_postgres()

# This file is correct and ready for use on Render or locally.
