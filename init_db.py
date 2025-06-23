import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        # For Render or cloud deployment
        import urllib.parse
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        result = urllib.parse.urlparse(url)
        conn = psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'
        )
        return conn
    else:
        # Local fallback
        return psycopg2.connect(
            host='localhost',
            dbname='postgres',
            user='postgres',
            password='12Marks@255'
        )

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Users Table (with role column)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                cisf_no TEXT,
                rank TEXT,
                mobile TEXT,
                role TEXT DEFAULT 'user'
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

        # Head Office Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS head_office (
                id SERIAL PRIMARY KEY,
                head TEXT,
                office_name TEXT
            );
        """)

        # Item Category Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items_category (
                id SERIAL PRIMARY KEY,
                category_name TEXT NOT NULL
            );
        """)

        # Renewal Voucher Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS renewal_voucher (
                id SERIAL PRIMARY KEY,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                date TEXT NOT NULL,
                remarks TEXT,
                head TEXT,
                lp_no TEXT,
                office TEXT
            );
        """)

        conn.commit()
        conn.close()
        print("✅ All tables created successfully.")

    except Exception as e:
        print("❌ Error in init_db:", e)

if __name__ == "__main__":
    init_db()

