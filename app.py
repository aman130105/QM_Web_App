from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import psycopg2.extras
from datetime import datetime
import io
from flask import send_file
import openpyxl

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # इसे strong key से बदलें

# DB connection settings for PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'postgres',  # <-- Use your actual database name, e.g. 'postgres' or 'mydb'
    'user': 'postgres',    # <-- Use your actual PostgreSQL username
    'password': '12Marks@255'  # <-- Your actual password
}

# Database helper
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# Helper for dict-like row access
def fetchall_dict(cur):
    return cur.fetchall()

def fetchone_dict(cur):
    return cur.fetchone()

# Home redirects to login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid Username or Password'

    return render_template('login.html', error=error)

# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if user already exists
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        if user:
            error = "Username already exists."
        else:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html', error=error)

# Dashboard Page
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    # Pass url_for('report') to template for the report button/link
    return render_template('dashboard.html', username=session['user'])

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/receive', methods=['GET', 'POST'])
def receive():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        category = request.form['category']
        item_name = request.form['item_name']
        head = request.form['head']
        ledger_page_no = request.form['ledger_page_no']
        available_stock = request.form['available_stock']
        qty = request.form['qty']
        price_unit = request.form['price_unit']
        remarks = request.form['remarks']
        date = request.form['date']

        cur.execute("""INSERT INTO received_items 
            (category, item_name, head, ledger_page_no, available_stock, qty, price_unit, remarks, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (category, item_name, head, ledger_page_no, available_stock, qty, price_unit, remarks, date))
        conn.commit()
        conn.close()
        return redirect(url_for('receive'))

    # Entries for table
    cur.execute("SELECT * FROM received_items ORDER BY id DESC")
    entries = cur.fetchall()
    entries = [dict(row) for row in entries]  # <-- Fix for JSON serialization

    categories = Ledger.get_categories()
    items_by_category = {cat: Ledger.get_items_by_category(cat) for cat in categories}
    conn.close()
    return render_template(
        'receive.html',
        categories=categories,
        items_by_category=items_by_category,
        entries=entries
    )

@app.route('/issue', methods=['GET', 'POST'])
def issue():
    error = None
    message = None
    form_data = {}

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        category = request.form['category']
        item_name = request.form['item_name']
        head = request.form['head']
        ledger_page_no = request.form['ledger_page_no']
        available_stock = request.form['available_stock']
        qty = int(request.form['qty'])
        issued_to = request.form['issued_to']
        date = request.form['date']
        remarks = request.form['remarks']

        # Calculate available stock for this item
        cur.execute("SELECT SUM(qty) as total_received FROM received_items WHERE category=%s AND item_name=%s", (category, item_name))
        received = cur.fetchone()['total_received'] or 0
        cur.execute("SELECT SUM(qty) as total_issued FROM issued_items WHERE category=%s AND item_name=%s", (category, item_name))
        issued = cur.fetchone()['total_issued'] or 0
        available = received - issued

        if qty > available:
            error = f"Issue quantity ({qty}) cannot be greater than available stock ({available})."
            # Keep form data so user doesn't have to re-enter
            form_data = request.form.to_dict()
        else:
            # Save entry
            cur.execute("""
                INSERT INTO issued_items (category, item_name, head, ledger_page_no, available_stock, qty, issued_to, date, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (category, item_name, head, ledger_page_no, available_stock, qty, issued_to, date, remarks))
            conn.commit()
            message = "Entry added successfully."
            form_data = {}  # Clear form

    # Fetch all issued items for table
    cur.execute("SELECT * FROM issued_items ORDER BY id DESC")
    entries = cur.fetchall()
    entries = [dict(row) for row in entries]

    categories = Ledger.get_categories()
    items_by_category = {cat: Ledger.get_items_by_category(cat) for cat in categories}
    offices = HeadOfficeManager.get_all_offices()
    conn.close()
    return render_template(
        'issue.html',
        categories=categories,
        items_by_category=items_by_category,
        entries=entries,
        error=error,
        message=message,
        form_data=form_data,
        offices=offices
    )

class UserManager:
    @staticmethod
    def get_all_users():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, username FROM users")
        users = cur.fetchall()
        conn.close()
        return [dict(row) for row in users]

    @staticmethod
    def add_user(username, password):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_user(user_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()

@app.route('/users')
def user_list():
    if 'user' not in session:
        return redirect(url_for('login'))
    users = UserManager.get_all_users()
    return render_template('user_list.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user' not in session:
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        UserManager.add_user(username, password)
        message = "User added successfully."
    return render_template('add_user.html', message=message)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    UserManager.delete_user(user_id)
    return redirect(url_for('user_list'))

@app.route('/ledger', methods=['GET', 'POST'])
def ledger():
    if 'user' not in session:
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        category = request.form['category']
        item_name = request.form['item_name']
        head = request.form['head']
        ledger_page_no = request.form['ledger_page_no']
        opening_date = request.form['opening_date']
        Ledger.add(category, item_name, head, ledger_page_no, opening_date)
        message = "Ledger entry added successfully."
    items = Ledger.get_all()

    # Fetch categories from items_category table
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT category_name FROM items_category ORDER BY category_name")
    categories = [row['category_name'] for row in cur.fetchall()]
    # Fetch heads from head_office table
    cur.execute("SELECT head FROM head_office WHERE head IS NOT NULL AND head != '' ORDER BY head")
    heads = [row['head'] for row in cur.fetchall()]
    conn.close()

    return render_template(
        'ledger.html',
        items=items,
        categories=categories,
        heads=heads,
        message=message,
        now=datetime.now
    )
# ...existing code...

class Ledger:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM ledger")
        items = cur.fetchall()
        conn.close()
        return [dict(row) for row in items]

    @staticmethod
    def add(category, item_name, head, ledger_page_no, opening_date):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ledger (category, item_name, head, ledger_page_no, opening_date) VALUES (%s, %s, %s, %s, %s)",
            (category, item_name, head, ledger_page_no, opening_date)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_categories():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT DISTINCT category FROM ledger")
        categories = [row['category'] for row in cur.fetchall()]
        conn.close()
        return categories

    @staticmethod
    def get_items_by_category(category):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT item_name FROM ledger WHERE category = %s", (category,))
        items = [row['item_name'] for row in cur.fetchall()]
        conn.close()
        return items

def create_ledger_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            head TEXT,
            ledger_page_no TEXT,
            opening_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_received_items_table():
    conn = get_db_connection()
    cur = conn.cursor()
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
        )
    """)
    conn.commit()
    conn.close()

def recreate_issued_items_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS issued_items")
    cur.execute("""
        CREATE TABLE issued_items (
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
        )
    """)
    conn.commit()
    conn.close()

def create_head_office_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS head_office (
            id SERIAL PRIMARY KEY,
            head TEXT,
            office_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_ledger_entries_table():
    conn = get_db_connection()
    cur = conn.cursor()
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
        )
    """)
    conn.commit()
    conn.close()

def create_items_category_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items_category (
            id SERIAL PRIMARY KEY,
            category_name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.route('/update_ledger/<int:id>', methods=['GET', 'POST'])
def update_ledger(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        category = request.form['category']
        item_name = request.form['item_name']
        head = request.form['head']
        ledger_page_no = request.form['ledger_page_no']
        opening_date = request.form['opening_date']
        cur.execute("""
            UPDATE ledger SET category=%s, item_name=%s, head=%s, ledger_page_no=%s, opening_date=%s
            WHERE id=%s
        """, (category, item_name, head, ledger_page_no, opening_date, id))
        conn.commit()
        conn.close()
        return redirect(url_for('ledger'))
    cur.execute("SELECT * FROM ledger WHERE id=%s", (id,))
    item = cur.fetchone()
    # Fetch categories and heads for dropdowns
    cur.execute("SELECT category_name FROM items_category ORDER BY category_name")
    categories = [row['category_name'] for row in cur.fetchall()]
    cur.execute("SELECT head FROM head_office WHERE head IS NOT NULL AND head != '' ORDER BY head")
    heads = [row['head'] for row in cur.fetchall()]
    conn.close()
    return render_template('update_ledger.html', item=item, categories=categories, heads=heads, now=datetime.now)

@app.route('/delete_ledger/<int:id>', methods=['POST'])
def delete_ledger(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ledger WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ledger'))

@app.route('/update_receive/<int:id>', methods=['GET', 'POST'])
def update_receive(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        # Update fields as per your receive table
        category = request.form['category']
        item_name = request.form['item_name']
        head = request.form['head']
        ledger_page_no = request.form['ledger_page_no']
        available_stock = request.form['available_stock']
        qty = request.form['qty']
        price_unit = request.form['price_unit']
        remarks = request.form['remarks']
        date = request.form['date']
        cur.execute("""
            UPDATE received_items SET category=%s, item_name=%s, head=%s, ledger_page_no=%s, available_stock=%s, qty=%s, price_unit=%s, remarks=%s, date=%s
            WHERE id=%s
        """, (category, item_name, head, ledger_page_no, available_stock, qty, price_unit, remarks, date, id))
        conn.commit()
        conn.close()
        return redirect(url_for('receive'))
    cur.execute("SELECT * FROM received_items WHERE id=%s", (id,))
    entry = cur.fetchone()
    conn.close()
    return render_template('update_receive.html', entry=entry)

@app.route('/delete_receive/<int:id>', methods=['POST'])
def delete_receive(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM received_items WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('receive'))

@app.route('/update_issue/<int:id>', methods=['GET', 'POST'])
def update_issue(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        category = request.form['category']
        item_name = request.form['item_name']
        qty = int(request.form['qty'])
        issued_to = request.form['issued_to']
        date = request.form['date']
        remarks = request.form['remarks']
        cur.execute("""
            UPDATE issued_items SET category=%s, item_name=%s, qty=%s, issued_to=%s, date=%s, remarks=%s
            WHERE id=%s
        """, (category, item_name, qty, issued_to, date, remarks, id))
        conn.commit()
        conn.close()
        return redirect(url_for('issue'))
    cur.execute("SELECT * FROM issued_items WHERE id=%s", (id,))
    entry = cur.fetchone()
    conn.close()
    return render_template('update_issue.html', entry=entry)

@app.route('/delete_issue/<int:id>', methods=['POST'])
def delete_issue(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM issued_items WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('issue'))

@app.route('/get_ledger_info', methods=['POST'])
def get_ledger_info():
    category = request.form['category']
    item_name = request.form['item_name']
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Ledger info fetch
    cur.execute("SELECT head, ledger_page_no FROM ledger WHERE category=%s AND item_name=%s", (category, item_name))
    row = cur.fetchone()
    # Available stock calculation
    cur.execute("SELECT SUM(qty) as total_received FROM received_items WHERE category=%s AND item_name=%s", (category, item_name))
    received = cur.fetchone()['total_received'] or 0
    cur.execute("SELECT SUM(qty) as total_issued FROM issued_items WHERE category=%s AND item_name=%s", (category, item_name))
    issued = cur.fetchone()['total_issued'] or 0
    available_stock = received - issued
    conn.close()
    if row:
        return jsonify({
            'head': row['head'],
            'ledger_page_no': row['ledger_page_no'],
            'available_stock': available_stock
        })
    else:
        return jsonify({'head': '', 'ledger_page_no': '', 'available_stock': ''})

@app.route('/manage_head_office', methods=['GET', 'POST'])
def manage_head_office():
    if 'user' not in session:
        return redirect(url_for('login'))

    message = None
    head_form_value = ''
    office_form_value = ''
    head_id = ''
    office_id = ''

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        action = request.form.get('action')

        # HEAD CRUD
        if form_type == 'head':
            head = request.form.get('head', '').strip()
            head_id = request.form.get('head_id', '')
            if action == 'save' and head:
                HeadOfficeManager.add(head, '')
                message = "Head added successfully."
            elif action == 'update' and head_id and head:
                HeadOfficeManager.update(head_id, head, '')
                message = "Head updated successfully."
            elif action == 'delete' and head_id:
                HeadOfficeManager.delete(head_id)
                message = "Head deleted successfully."
            head_form_value = head

        # OFFICE CRUD
        elif form_type == 'office':
            office_name = request.form.get('office_name', '').strip()
            office_id = request.form.get('office_id', '')
            if action == 'save' and office_name:
                HeadOfficeManager.add('', office_name)
                message = "Office added successfully."
            elif action == 'update' and office_id and office_name:
                HeadOfficeManager.update(office_id, '', office_name)
                message = "Office updated successfully."
            elif action == 'delete' and office_id:
                HeadOfficeManager.delete(office_id)
                message = "Office deleted successfully."
            office_form_value = office_name

        # SELECT HEAD FOR UPDATE/DELETE
        elif form_type == 'head_select':
            head_id = request.form.get('head_id')
            head_row = HeadOfficeManager.get_by_id(head_id)
            if head_row:
                head_form_value = head_row['head']
                head_id = head_row['id']

        # SELECT OFFICE FOR UPDATE/DELETE
        elif form_type == 'office_select':
            office_id = request.form.get('office_id')
            office_row = HeadOfficeManager.get_by_id(office_id)
            if office_row:
                office_form_value = office_row['office_name']
                office_id = office_row['id']

    # Fetch all heads and offices
    heads = HeadOfficeManager.get_all_heads()
    offices = HeadOfficeManager.get_all_offices()
    return render_template(
        'manage_head_office.html',
        heads=heads,
        offices=offices,
        message=message,
        head_form_value=head_form_value,
        office_form_value=office_form_value,
        head_id=head_id,
        office_id=office_id
    )

@app.route('/update_head_office/<int:id>', methods=['GET', 'POST'])
def update_head_office(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        head = request.form['head']
        office_name = request.form['office_name']
        HeadOfficeManager.update(id, head, office_name)
        return redirect(url_for('manage_head_office'))
    cur.execute("SELECT * FROM head_office WHERE id=%s", (id,))
    entry = cur.fetchone()
    conn.close()
    return render_template('update_head_office.html', entry=entry)

@app.route('/delete_head_office/<int:id>', methods=['POST'])
def delete_head_office(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    HeadOfficeManager.delete(id)
    return redirect(url_for('manage_head_office'))

@app.route('/report')
def report():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Filters from request
    category = request.args.get('category', '')
    item = request.args.get('item', '')
    head = request.args.get('head', '')
    office = request.args.get('office', '')
    from_date = request.args.get('from_date', '2000-01-01')
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Prepare WHERE clause
    where = []
    params = []
    if category:
        where.append("category=%s")
        params.append(category)
    if item:
        where.append("item_name=%s")
        params.append(item)
    if head:
        where.append("head=%s")
        params.append(head)
    if office:
        where.append("issued_to=%s")
        params.append(office)
    where.append("date BETWEEN %s AND %s")
    params.extend([from_date, to_date])

    where_clause = " AND ".join(where) if where else "1=1"

    # Fix: Use NULL for integer columns in UNION, not empty string
    query = f"""
        SELECT date, 'Receive' as type, item_name as item, remarks as description, head, ledger_page_no as lp_no,
               NULL as previous, qty as received, NULL as issued, NULL as office
        FROM received_items
        WHERE {where_clause}
        UNION ALL
        SELECT date, 'Issue' as type, item_name as item, remarks as description, head, ledger_page_no as lp_no,
               NULL as previous, NULL as received, qty as issued, issued_to as office
        FROM issued_items
        WHERE {where_clause}
        ORDER BY date DESC
    """
    cur.execute(query, params * 2)  # params for both SELECTs
    transactions = [dict(row) for row in cur.fetchall()]

    # For filters
    cur.execute("SELECT DISTINCT category FROM ledger")
    categories = [row['category'] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT item_name FROM ledger")
    items = [row['item_name'] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT head FROM ledger")
    heads = [row['head'] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT issued_to FROM issued_items")
    offices = [row['issued_to'] for row in cur.fetchall()]

    # Totals
    cur.execute("SELECT SUM(qty) FROM received_items")
    total_received = cur.fetchone()['sum'] or 0 if cur.rowcount else 0
    cur.execute("SELECT SUM(qty) FROM issued_items")
    total_issued = cur.fetchone()['sum'] or 0 if cur.rowcount else 0
    total_balance = total_received - total_issued

    conn.close()

    return render_template(
        'report.html',
        transactions=transactions,
        categories=categories,
        items=items,
        heads=heads,
        offices=offices,
        total_received=total_received,
        total_issued=total_issued,
        total_balance=total_balance,
        now=datetime.now
    )

class HeadOfficeManager:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM head_office")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_heads():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, head FROM head_office WHERE head != ''")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_offices():
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, office_name FROM head_office WHERE office_name != ''")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add(head, office_name):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO head_office (head, office_name) VALUES (%s, %s)", (head, office_name))
        conn.commit()
        conn.close()

    @staticmethod
    def update(id, head, office_name):
        conn = get_db_connection()
        cur = conn.cursor()
        if head:
            cur.execute("UPDATE head_office SET head=%s WHERE id=%s", (head, id))
        elif office_name:
            cur.execute("UPDATE head_office SET office_name=%s WHERE id=%s", (office_name, id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM head_office WHERE id=%s", (id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_id(id):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM head_office WHERE id=%s", (id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

# Yeh function app.run se pehle ek baar call kar dein:
@app.route('/export_excel')
def export_excel():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Same filters as report
    category = request.args.get('category', '')
    item = request.args.get('item', '')
    head = request.args.get('head', '')
    office = request.args.get('office', '')
    from_date = request.args.get('from_date', '2000-01-01')
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))

    conn = get_db_connection()
    cur = conn.cursor()

    where = []
    params = []
    if category:
        where.append("category=%s")
        params.append(category)
    if item:
        where.append("item_name=%s")
        params.append(item)
    if head:
        where.append("head=%s")
        params.append(head)
    if office:
        where.append("issued_to=%s")
        params.append(office)
    where.append("date BETWEEN %s AND %s")
    params.extend([from_date, to_date])
    where_clause = " AND ".join(where) if where else "1=1"

    query = f"""
        SELECT date, 'Receive' as type, item_name as item, remarks as description, head, ledger_page_no as lp_no,
               NULL as previous, qty as received, NULL as issued, NULL as office
        FROM received_items
        WHERE {where_clause}
        UNION ALL
        SELECT date, 'Issue' as type, item_name as item, remarks as description, head, ledger_page_no as lp_no,
               NULL as previous, NULL as received, qty as issued, issued_to as office
        FROM issued_items
        WHERE {where_clause}
        ORDER BY date DESC
    """
    cur.execute(query, params * 2)
    rows = cur.fetchall()
    conn.close()

    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Transaction Report"
    headers = ["Date", "Type", "Item", "Description", "Head", "L/P No.", "Previous", "Received", "Issue", "Office"]
    ws.append(headers)
    for row in rows:
        ws.append([
            row["date"], row["type"], row["item"], row["description"], row["head"], row["lp_no"],
            row["previous"], row["received"], row["issued"], row["office"]
        ])

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="transaction_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/export_ledger_excel')
def export_ledger_excel():
    if 'user' not in session:
        return redirect(url_for('login'))
    item = request.args.get('item', '')
    if not item:
        return "No item selected", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ledger_entries WHERE item_name = %s ORDER BY date", (item,))
    rows = cur.fetchall()
    conn.close()

    import openpyxl
    import io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ledger"
    headers = ["S.No", "Date", "Type", "Receive From", "Issue To", "Prev Bal", "Receive Qty", "Issue Qty", "Balance", "Remark"]
    ws.append(headers)
    for idx, row in enumerate(rows, 1):
        ws.append([
            idx, row['date'], row['type'], row['receive_from'], row['issue_to'],
            row['prev_bal'], row['receive_qty'], row['issue_qty'], row['balance'], row['remark']
        ])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    from flask import send_file
    return send_file(
        output,
        as_attachment=True,
        download_name=f"ledger_{item}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/export_pdf')
def export_pdf():
    return "PDF export coming soon!"

def get_all_items():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT DISTINCT item_name FROM ledger")
    items = [row['item_name'] for row in cur.fetchall()]
    conn.close()
    return items

@app.route('/print_ledger', methods=['GET', 'POST'])
def print_ledger():
    selected_item = request.args.get('item')
    items = get_all_items()  # function jo item list deta hai

    ledger_data = []
    item_info = None

    if selected_item:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM ledger_entries WHERE item_name = %s ORDER BY date", (selected_item,))
        ledger_data = [dict(row) for row in cur.fetchall()]
        # item_info fetch karne ka code bhi yahan hona chahiye
        cur.execute("SELECT * FROM items WHERE item_name = %s", (selected_item,))
        item_info = cur.fetchone()
        conn.close()

    return render_template(
        'print_ledger.html',
        items=items,
        selected_item=selected_item,
        ledger_data=ledger_data,
        item_info=item_info
    )

@app.route('/export_ledger_pdf')
def export_ledger_pdf():
    if 'user' not in session:
        return redirect(url_for('login'))
    item = request.args.get('item', '')
    if not item:
        return "No item selected", 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ledger WHERE item_name = %s", (item,))
    item_info = cur.fetchone()
    cur.execute("SELECT * FROM ledger_entries WHERE item_name = %s ORDER BY date", (item,))
    rows = cur.fetchall()
    conn.close()

    # Render HTML for PDF (Image1 layout)
    from flask import render_template
    html = render_template('ledger_pdf_template.html', item_info=item_info, rows=rows)

    # Use pdfkit/weasyprint to generate PDF from HTML
    import pdfkit
    import io
    pdf = pdfkit.from_string(html, False)
    return send_file(
        io.BytesIO(pdf),
        as_attachment=True,
        download_name=f"ledger_{item}.pdf",
        mimetype="application/pdf"
    )

@app.route('/items_category', methods=['GET', 'POST'])
def items_category():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    # Use RealDictCursor for dict-like rows
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    message = ""
    if request.method == 'POST':
        category_name = request.form['category_name'].strip()
        if category_name:
            cur.execute("INSERT INTO items_category (category_name) VALUES (%s)", (category_name,))
            conn.commit()
            message = "Category added successfully."
        else:
            message = "Category name cannot be empty."
    cur.execute("SELECT * FROM items_category ORDER BY id DESC")
    categories = [dict(row) for row in cur.fetchall()]
    conn.close()
    return render_template('items_category.html', categories=categories, message=message)

@app.route('/update_category/<int:id>', methods=['GET', 'POST'])
def update_category(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        category_name = request.form['category_name'].strip()
        if category_name:
            cur.execute("UPDATE items_category SET category_name=%s WHERE id=%s", (category_name, id))
            conn.commit()
            conn.close()
            return redirect(url_for('items_category'))
    cur.execute("SELECT * FROM items_category WHERE id=%s", (id,))
    category = cur.fetchone()
    conn.close()
    return render_template('update_items_category.html', category=category)

@app.route('/delete_category/<int:id>', methods=['POST'])
def delete_category(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items_category WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('items_category'))

# ---- THIS BLOCK MUST BE LAST ----
if __name__ == '__main__':
    create_ledger_table()
    create_received_items_table()
    create_items_category_table()  # <-- yeh line add karein
    create_head_office_table()
    create_ledger_entries_table()
    app.run(debug=True)


