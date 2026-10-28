import sqlite3
import threading
from datetime import datetime, timedelta
from config import DB_PATH

_local = threading.local()

def db():
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, phone TEXT,
            acc_created TEXT, joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP, is_banned INTEGER DEFAULT 0,
            ban_until DATETIME DEFAULT NULL, refer_code TEXT, referred_by INTEGER, last_daily DATETIME DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS user_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER, used_at DATETIME);
        CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task TEXT, status INTEGER DEFAULT 0);
    """)
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.commit()

def log_user(message):
    uid = message.from_user.id
    fn = message.from_user.first_name or "بێ ناو"
    un = message.from_user.username or "بێ یوزەرنەیم"
    db().execute("""
        INSERT OR IGNORE INTO users (user_id, first_name, username, acc_created, refer_code) 
        VALUES (?, ?, ?, datetime('now', 'localtime'), ?)
    """, (uid, fn, un, f"ref_{uid}"))
    db().execute("UPDATE users SET first_name=?, username=?, last_seen=datetime('now', 'localtime') WHERE user_id=?", (fn, un, uid))
    db().commit()

def get_setting(key):
    row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, val):
    db().execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
    db().commit()

def add_credit(user_id, n):
    db().execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=questions_left+?", (user_id, n, n))
    db().commit()

def spend_credit(user_id):
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (user_id,)).fetchone()
    if row and row[0] > 0:
        db().execute("UPDATE credit SET questions_left=questions_left-1 WHERE user_id=?", (user_id,))
        db().commit()
        return True
    return False
