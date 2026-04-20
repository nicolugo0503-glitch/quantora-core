
import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "quantora.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS accounts (user_id TEXT, capital REAL, pnl REAL)")
    conn.commit()
    conn.close()
