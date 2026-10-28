import sqlite3
import threading
import datetime
import random
import re
import config
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
        CREATE TABLE IF NOT EXISTS simple_admins (user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS user_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER, used_at DATETIME);
        CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task TEXT, status INTEGER DEFAULT 0);
    """)
    
    # ئەم بەشە بۆ دڵنیابوونە لەوەی کۆڵۆنە نوێیەکان زیادکراون ئەگەر داتابەیسە کۆنەکە هەبوو
    try: c.execute("ALTER TABLE users ADD COLUMN last_seen DATETIME DEFAULT CURRENT_TIMESTAMP")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN last_daily DATETIME DEFAULT NULL")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN refer_code TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except: pass

    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.commit()

def log_user(message):
    uid = message.from_user.id
    fn = message.from_user.first_name or "بێ ناو"
    un = message.from_user.username or "بێ یوزەرنەیم"
    c = db()
    cursor = c.execute("""
        INSERT OR IGNORE INTO users (user_id, first_name, username, acc_created, refer_code) 
        VALUES (?, ?, ?, datetime('now', 'localtime'), ?)
    """, (uid, fn, un, f"ref_{uid}"))
    is_new_user = cursor.rowcount > 0
    c.execute("UPDATE users SET first_name=?, username=?, last_seen=datetime('now', 'localtime') WHERE user_id=?", (fn, un, uid))
    c.commit()
    return is_new_user

def get_setting(key):
    row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, val):
    db().execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
    db().commit()

def add_credit(user_id, n):
    db().execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=questions_left+?", (user_id, n, n))
    db().commit()

def is_simple_admin(uid):
    # سەرەتا لە کۆنفیگ چێک دەکات (ئەگەر ئایدییەکەی تێدا دابنرابێت)
    if uid in getattr(config, 'SIMPLE_ADMINS', []):
        return True
    # دواتر لە داتابەیس چێک دەکات
    row = db().execute("SELECT user_id FROM simple_admins WHERE user_id=?", (uid,)).fetchone()
    return row is not None

def spend_credit(user_id):
    # ئەگەر ئەدمینی سەرەکی یان ئەدمینی سادە بێت، هەرگیز کرێدیتی لێ کەم نابێت
    if is_simple_admin(user_id) or user_id == config.ADMIN_ID:
        return True
        
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (user_id,)).fetchone()
    if row and row[0] > 0:
        db().execute("UPDATE credit SET questions_left=questions_left-1 WHERE user_id=?", (user_id,))
        db().commit()
        return True
    return False

def remove_credit(user_id, n):
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (user_id,)).fetchone()
    if row and row[0] > 0:
        new_val = max(0, row[0] - n)
        db().execute("UPDATE credit SET questions_left=? WHERE user_id=?", (new_val, user_id))
        db().commit()
        return True
    return False

def set_credit(user_id, n):
    db().execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=?", (user_id, n, n))
    db().commit()

def create_gift(reward=10):
    code = f"BUGFIX-{random.randint(1000, 9999)}-{random.choice('XZKM')}{random.randint(100, 999)}"
    db().execute("INSERT INTO gift_codes(code, reward) VALUES(?,?)", (code, reward))
    db().commit()
    return code

def redeem_gift(user_id, code):
    row = db().execute("SELECT used_by, reward FROM gift_codes WHERE code=?", (code.strip(),)).fetchone()
    if not row: return False, "کۆدی نەناسراو", 0
    if row[0] is not None: return False, "ئەم کۆدە پێشتر بەکارهاتووە", 0
    db().execute("UPDATE gift_codes SET used_by=?, used_at=CURRENT_TIMESTAMP WHERE code=?", (user_id, code))
    db().commit()
    add_credit(user_id, row[1])
    return True, "ok", row[1]

def check_ban(uid):
    row = db().execute("SELECT is_banned, ban_until FROM users WHERE user_id=?", (uid,)).fetchone()
    if not row or row[0] == 0: return False, None
    ban_until = row[1]
    if ban_until is None: return True, "هەتا هەتای"
    try:
        now = datetime.datetime.now()
        until = datetime.datetime.strptime(ban_until, "%Y-%m-%d %H:%M:%S")
        if now > until:
            db().execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (uid,))
            db().commit()
            return False, None
        return True, ban_until
    except ValueError:
        db().execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (uid,))
        db().commit()
        return False, None

def parse_ban_time(time_str):
    time_str = time_str.lower().strip()
    if time_str == "0": return None
    match = re.match(r'^(\d+)([mhdw]|mo)$', time_str)
    if not match: return False
    val = int(match.group(1))
    unit = match.group(2)
    now = datetime.datetime.now()
    if unit == 'm': return (now + datetime.timedelta(minutes=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'h': return (now + datetime.timedelta(hours=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'd': return (now + datetime.timedelta(days=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'w': return (now + datetime.timedelta(weeks=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'mo': return (now + datetime.timedelta(days=val*30)).strftime("%Y-%m-%d %H:%M:%S")
    return False
