import sqlite3

conn = sqlite3.connect('cisf_qm.db')  # आपकी SQLite DB फाइल
cur = conn.cursor()

cur.execute("PRAGMA table_info(items)")
for column in cur.fetchall():
    print(column)
