import os
import sys
import random
import sqlite3
import logging
import html
import threading
import urllib.parse
import urllib.request
import re
import time
from datetime import datetime, timedelta

import telebot
from telebot import types

# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
DB_PATH = "bot_database.db"
# ==========================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("UltimateGodTierCore")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
_local = threading.local()

# ==========================================
# 1. داتابەیس
# ==========================================
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
            user_id INTEGER PRIMARY KEY, 
            first_name TEXT, 
            username TEXT, 
            phone TEXT,
            acc_created TEXT,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            ban_until DATETIME DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS user_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_mem ON user_memory(user_id, id DESC);
        CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER, used_at DATETIME);
        CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    """)
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.commit()

def log_user(message):
    uid = message.from_user.id
    fn = message.from_user.first_name or "بێ ناو"
    un = message.from_user.username or "بێ یوزەرنەیم"
    
    phone = "نەزانراو"
    try:
        chat_info = bot.get_chat(uid)
        phone = getattr(chat_info, 'phone_number', None) or "نەزانراو"
    except Exception:
        pass
        
    db().execute("""
        INSERT OR IGNORE INTO users (user_id, first_name, username, phone, acc_created) 
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
    """, (uid, fn, un, phone))
    
    db().execute("""
        UPDATE users SET first_name=?, username=?, phone=? WHERE user_id=?
    """, (fn, un, phone, uid))
    db().commit()

def get_bot_status():
    row = db().execute("SELECT value FROM settings WHERE key='bot_status'").fetchone()
    return row[0] if row else "on"

def set_bot_status(status):
    db().execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (status,))
    db().commit()

def check_ban(uid):
    row = db().execute("SELECT is_banned, ban_until FROM users WHERE user_id=?", (uid,)).fetchone()
    if not row or row[0] == 0:
        return False, None
    
    ban_until = row[1]
    if ban_until is None:
        return True, "هەتا هەتای"
        
    try:
        now = datetime.now()
        until = datetime.strptime(ban_until, "%Y-%m-%d %H:%M:%S")
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
    if time_str == "0":
        return None
    match = re.match(r'^(\d+)([mhdw]|mo)$', time_str)
    if not match:
        return False
    val = int(match.group(1))
    unit = match.group(2)
    now = datetime.now()
    if unit == 'm':
        return (now + timedelta(minutes=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'h':
        return (now + timedelta(hours=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'd':
        return (now + timedelta(days=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'w':
        return (now + timedelta(weeks=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'mo':
        return (now + timedelta(days=val*30)).strftime("%Y-%m-%d %H:%M:%S")
    return False

# ==========================================
# 2. فەنکشنەکانی داتابەیس
# ==========================================
def set_state(user_id, state, data=""):
    db().execute("INSERT OR REPLACE INTO user_states(user_id, state, data) VALUES(?,?,?)", (user_id, state, data))
    db().commit()

def get_state(user_id):
    row = db().execute("SELECT state, data FROM user_states WHERE user_id=?", (user_id,)).fetchone()
    return (row[0], row[1]) if row else (None, "")

def clear_state(user_id):
    db().execute("DELETE FROM user_states WHERE user_id=?", (user_id,))
    db().commit()

def add_credit(user_id, n):
    db().execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=questions_left+?", (user_id, n, n))
    db().commit()

def remove_credit(user_id, n):
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (user_id,)).fetchone()
    if row and row[0] > 0:
        new_val = max(0, row[0] - n)
        db().execute("UPDATE credit SET questions_left=? WHERE user_id=?", (new_val, user_id))
        db().commit()
        return True
    return False

def spend_credit(user_id):
    return remove_credit(user_id, 1)

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

# ==========================================
# 3. یارمەتیدەر و گەڕان
# ==========================================
def get_signature():
    return (
        "\n\n───────────────────\n"
        "🛡 <b>[BLACK HAT AI SECURITY CORE]</b>\n"
        "🎁 بۆ بەکارهێنانی کۆدی خەڵات: <code>/gift [کۆد]</code>\n"
        "👑 <b>پەیوەندی:</b> @malikdlashad3 | @ALONE427"
    )

TOPICS = {"it", "cyber", "security", "hack", "هاک", "سایبەر", "network", "تۆڕ", "linux", "windows", "python", "script", "kali", "nmap", "sqlmap", "html", "css", "js", "php", "sql", "java", "c++", "c#", "web", "وێب", "سایت", "code", "کۆد", "ddos", "wifi", "وایفای", "exploit", "payload", "پەیلوود", "vulnerability", "لاوازی", "malware", "database", "encryption", "پاسوۆرد", "bug", "باگ"}

def is_allowed(q):
    return any(k in q.lower() for k in TOPICS)

LANG_MAP = {"html": "HTML", "css": "CSS", "js": "JS", "javascript": "JavaScript", "php": "PHP", "python": "Python", "react": "React"}

def _web_template(lang):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Design — {lang}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',Tahoma,sans-serif}}
    body{{background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;min-height:100vh}}
    .box{{background:#161b22;width:min(450px,92vw);padding:40px;border-radius:12px;border:1px solid #30363d;box-shadow:0 8px 30px rgba(0,0,0,.8)}}
    .btn{{background:#238636;color:#fff;border:0;padding:12px 24px;border-radius:6px;font-weight:700;cursor:pointer;width:100%}}
    .btn:hover{{background:#2ea043}}
  </style>
</head>
<body>
  <div class="box">
    <h2 style="margin-bottom:16px">Design — {lang}</h2>
    <button class="btn">Choose file</button>
  </div>
</body>
</html>"""

def _search_snippets(query, timeout=8):
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html_resp = resp.read().decode("utf-8", "ignore")
        snips = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_resp, re.DOTALL)
        return [re.sub(r"<.*?>", "", s).strip() for s in snips[:3] if s.strip()]
    except Exception as e:
        logger.warning("Search failed: %s", e)
        return []

def make_professional_response(query, snippets):
    intro = random.choice([
        "بەخێربێیت بۆ سیستەمی شیکاری ئاسایش.",
        "داواکارییەکەت وەرگیرا. لە خوارەوە شیکاری تەکنیکی هاتووە:",
        "سیستەمی زیرەک داواکارییەکەی پشکنی و ئەم ئەنجامەی دۆزییەوە:",
        "وردبینی تەکنیکی تەواو بوو. ئەم زانیارییانە لەبارەی پرسیارەکەتەوە هاتووە:"
    ])
    body = "\n\n".join([f"• {s}" for s in snippets]) if snippets else (
        f"لە ڕوانگەی ئاسایش و پڕۆگرامسازییەوە، بابەتی (<b>{html.escape(query)}</b>) "
        f"پەیوەندی بە بواری تەکنەلۆجیا هەیە. بۆ زانیاری زیاتر و وردبینی، "
        f"پێویستە پرسیارەکەت بە وردی زیاتر ڕوون بکەیتەوە یان کۆدی پەیوەندیدار بنێریت."
    )
    return f"🛡 <b>شیکاری ئاسایش و پڕۆگرامسازی:</b>\n\n<i>{intro}</i>\n\n{body}"

# ==========================================
# 4. پەنێلی ئەدمین
# ==========================================
@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if message.from_user.id != ADMIN_ID: return
    log_user(message)
    
    total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_codes = db().execute("SELECT COUNT(*) FROM gift_codes").fetchone()[0]
    used_codes = db().execute("SELECT COUNT(*) FROM gift_codes WHERE used_by IS NOT NULL").fetchone()[0]
    bot_status = get_bot_status()
    
    text = (
        f"👑 <b>پەنێلی سەرۆکایەتی (Admin Panel) — v52.0</b> 👑\n\n"
        f"👤 کۆی بەکارهێنەران: <b>{total_users}</b>\n"
        f"🎁 کۆدی خەڵات: <b>{total_codes}</b> (بەکارهاتوو: {used_codes})\n"
        f"⚙️ دۆخی بۆت: <b>{'✅ کارا' if bot_status == 'on' else '❌ ناچالاک'}</b>\n\n"
        f"📌 <b>فەرمانەکان:</b>\n\n"
        f"🔹 <code>/stats</code> — ئاماری سیستەم\n"
        f"🔹 <code>/members</code> — لیستی دوایین 50 ئەندام\n"
        f"🔹 <code>/user [ID]</code> — زانیاری وردی بەکارهێنەر\n"
        f"🔹 <code>/broadcast [نامە]</code> — ناردنی نامە بۆ هەمووان\n"
        f"🔹 <code>/addcredit [ID] [ژمارە]</code> — زیادکردنی کرێدیت\n"
        f"🔹 <code>/remcredit [ID] [ژمارە]</code> — کەمکردنەوەی کرێدیت\n"
        f"🔹 <code>/ban [ID] [کات]</code> — بلۆککردن (m, h, d, w, mo, 0)\n"
        f"🔹 <code>/unban [ID]</code> — کردنەوەی بلۆک\n"
        f"🔹 <code>/on</code> — کاراکردنی بۆت\n"
        f"🔹 <code>/off</code> — ناچالاککردنی بۆت\n"
        f"🔹 <code>/gen [ژمارە]</code> — دروستکردنی کۆدی خەڵات"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID: return
    users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned = db().execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
    msgs = db().execute("SELECT COUNT(*) FROM user_memory").fetchone()[0]
    bot.reply_to(message, f"📊 <b>ئامار:</b>\n\n👤 بەکارهێنەران: {users}\n🚫 بلۆککراوەکان: {banned}\n💬 نامەکان: {msgs}")

@bot.message_handler(commands=["members"])
def cmd_members(message):
    if message.from_user.id != ADMIN_ID: return
    rows = db().execute("SELECT user_id, first_name, username, is_banned, ban_until FROM users ORDER BY joined_at DESC LIMIT 50").fetchall()
    if not rows:
        bot.reply_to(message, "هیچ ئەندامێک نییە.")
        return
    text = "👥 <b>دوایین 50 ئەندام:</b>\n\n"
    for r in rows:
        uid, fn, un, banned, until = r
        un_str = f"@{un}" if un != "بێ یوزەرنەیم" else "بێ یوزەرنەیم"
        status = "✅"
        if banned:
            status = f"🚫 (تا: {until})" if until else "🚫 (هەتا هەتای)"
        text += f"{status} {fn} ({un_str}) - <code>{uid}</code>\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=["user"])
def cmd_user_info(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ تکایە ID بنووسە. نموونە: <code>/user 123456789</code>")
        return
        
    target_id = int(parts[1])
    row = db().execute("SELECT user_id, first_name, username, phone, acc_created, joined_at, is_banned, ban_until FROM users WHERE user_id=?", (target_id,)).fetchone()
    
    if not row:
        bot.reply_to(message, "❌ بەکارهێنەر نەدۆزرایەوە.")
        return
        
    uid, fn, un, phone, acc_created, joined_at, banned, until = row
    un_str = f"@{un}" if un != "بێ یوزەرنەیم" else "بێ یوزەرنەیم"
    status = "✅ ئاسایی"
    if banned:
        status = f"🚫 بلۆککراو (تا: {until})" if until else "🚫 بلۆککراو (هەتا هەتای)"
        
    text = (
        f"👤 <b>زانیاری بەکارهێنەر:</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"📝 ناو: {fn}\n"
        f"🔗 یوزەرنەیم: {un_str}\n"
        f"📞 ژمارە تەلەفۆن: {phone}\n"
        f"📅 بەرواری دروستکردنی ئەکاونت: {acc_created}\n"
        f"📥 بەرواری جۆینبوون لە بۆت: {joined_at}\n"
        f"⚙️ دۆخ: {status}"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ تکایە نامەکە بنووسە. نموونە:\n<code>/broadcast سڵاو بۆ هەمووان</code>")
        return
    msg_text = parts[1]
    users = db().execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    bot.reply_to(message, "⏳ دەستپێکردنی ناردن...")
    sent, failed = 0, 0
    for (uid,) in users:
        try:
            bot.send_message(uid, msg_text)
            sent += 1
        except Exception:
            failed += 1
    bot.reply_to(message, f"✅ نێردرا بۆ: {sent}\n❌ شکست: {failed}")

@bot.message_handler(func=lambda m: m.text.startswith("/زیادکردنی") or m.text.startswith("/addcredit"))
def cmd_add_credit(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/زیادکردنی", "").replace("/addcredit", "").strip()
    parts = text.split()
    
    if len(parts) < 3 or parts[0] != "کریدت" or not parts[1].isdigit() or not parts[2].isdigit():
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            target_id, amount = int(parts[0]), int(parts[1])
        else:
            bot.reply_to(message, "⚠️ شێواز هەڵەیە. بنووسە:\n<code>/زیادکردنی کریدت [ID] [ژمارە]</code>")
            return
    else:
        target_id, amount = int(parts[1]), int(parts[2])
        
    add_credit(target_id, amount)
    bot.reply_to(message, f"✅ <b>{amount}</b> کرێدیت زیادکرا بۆ <code>{target_id}</code>.")

@bot.message_handler(func=lambda m: m.text.startswith("/کەمکردنی") or m.text.startswith("/remcredit"))
def cmd_remove_credit(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/کەمکردنی", "").replace("/remcredit", "").strip()
    parts = text.split()
    
    if len(parts) < 3 or parts[0] != "کریدت" or not parts[1].isdigit() or not parts[2].isdigit():
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            target_id, amount = int(parts[0]), int(parts[1])
        else:
            bot.reply_to(message, "⚠️ شێواز هەڵەیە. بنووسە:\n<code>/کەمکردنی کریدت [ID] [ژمارە]</code>")
            return
    else:
        target_id, amount = int(parts[1]), int(parts[2])
        
    remove_credit(target_id, amount)
    bot.reply_to(message, f"✅ <b>{amount}</b> کرێدیت کەمکرایەوە لە <code>{target_id}</code>.")

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ تکایە ID و کات بنووسە. نموونە: <code>/ban 123456789 2d</code> (بۆ ۲ ڕۆژ، 0 بۆ هەتا هەتای)")
        return
    target_id = int(parts[1])
    time_str = parts[2] if len(parts) > 2 else "0"
    
    if target_id == ADMIN_ID:
        bot.reply_to(message, "❌ ناتوانیت خۆت بلۆک بکەیت!")
        return
        
    ban_until = parse_ban_time(time_str)
    if ban_until is False:
        bot.reply_to(message, "❌ کاتی نادروست. تکایە m، h، d، w، mo یان 0 بەکاربهێنە.")
        return
        
    if ban_until is None:
        db().execute("UPDATE users SET is_banned=1, ban_until=NULL WHERE user_id=?", (target_id,))
        bot.reply_to(message, f"🚫 بەکارهێنەر <code>{target_id}</code> بۆ هەتا هەتای بلۆک کرا.")
    else:
        db().execute("UPDATE users SET is_banned=1, ban_until=? WHERE user_id=?", (ban_until, target_id))
        bot.reply_to(message, f"🚫 بەکارهێنەر <code>{target_id}</code> بلۆک کرا.\n⏰ تا: {ban_until}")
    db().commit()

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ تکایە ID بنووسە. نموونە: <code>/unban 123456789</code>")
        return
    target_id = int(parts[1])
    db().execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (target_id,))
    db().commit()
    bot.reply_to(message, f"✅ بەکارهێنەر <code>{target_id}</code> کرایەوە.")

@bot.message_handler(commands=["on"])
def cmd_on(message):
    if message.from_user.id != ADMIN_ID: return
    set_bot_status("on")
    bot.reply_to(message, "✅ سیستەم کارا کرا. بۆت ئێستا بۆ هەمووان کار دەکات.")

@bot.message_handler(commands=["off"])
def cmd_off(message):
    if message.from_user.id != ADMIN_ID: return
    set_bot_status("off")
    bot.reply_to(message, "❌ سیستەم ناچالاک کرا. بۆت ئێستا تەنها بۆ تۆ وەڵام دەداتەوە.")

@bot.message_handler(commands=["gen"])
def cmd_gen(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    reward = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
    code = create_gift(reward)
    bot.reply_to(message, f"✅ کۆدی نوێ دروستکرا:\n<code>{code}</code>\n🎁 Reward: {reward}")

# ==========================================
# 5. هەندلەرەکانی بەکارهێنەر
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    log_user(message)
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    banned, until = check_ban(message.from_user.id)
    if banned and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, f"🚫 تۆ بلۆککراویت. کاتی کردنەوە: {until}")
        return
    bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI GOD-TIER CORE v52.0</b> 💀\n\nسیستەمەکە بە تەواوی نوێ کرایەوە.\n🌐 <b>وێب:</b> وێنەی دیزاین بنێرە، پاشان زمان بنووسە." + get_signature())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    log_user(message)
    
    help_text = (
        "🛠 <b>لیستی توڵەکان و فەرمانەکان:</b>\n\n"
        "🌐 <b>1. دروستکردنی وێبسایت (Web Design):</b>\n"
        "   وێنەیەکی دیزاین بنێرە، پاشان ناوی زمانەکە بنووسە (HTML, CSS, JS, PHP, Python, React) بۆ ئەوەی کۆدەکەت بۆ دروست بکەم.\n\n"
        "💻 <b>2. شیکاری ئاسایش و هەکینگ (Cyber Security & IT):</b>\n"
        "   هەر پرسیارێک لەبارەی هەکینگ، تۆڕ، سێرڤەر، لینوکس، یان پڕۆگرامسازی بنووسە، سیستەمەکە شیکاری تەکنیکی بۆ دەکات.\n\n"
        "🔍 <b>3. گەڕانی پێشکەوتوو:</b>\n"
        "   هەر بابەتێکی تەکنیکی بنووسە، بۆتەکە بە زیرەکی دەگەڕێت و پوختەی پێ دەدەیت.\n\n"
        "🎁 <b>4. سیستەمی خەڵات (Credits):</b>\n"
        "   <code>/gift [کۆد]</code> — بەکارهێنانی کۆدی خەڵات بۆ زیادکردنی پرسیار.\n"
        "   <code>/credit</code> — بینینی ژمارەی پرسیارەکانی خەڵاتی ماوە.\n\n"
        "👑 <b>5. پەیوەندی و پشتگیری:</b>\n"
        "   بۆ هەر کێشەیەک یان پرسیارێک، پەیوەندی بکە بە: @ALONE427 یان @malikdlashad3"
    )
    bot.reply_to(message, help_text + get_signature())

@bot.message_handler(commands=["gift"])
def cmd_gift(message):
    log_user(message)
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    banned, _ = check_ban(message.from_user.id)
    if banned and message.from_user.id != ADMIN_ID: return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "🎁 کۆدی خەڵات بنووسە: <code>/gift BUGFIX-1234-X100</code>")
        return
    ok, reason, reward = redeem_gift(message.from_user.id, parts[1])
    if ok:
        bot.reply_to(message, f"🎉 <b>پیرۆزە!</b> کۆدەکەت کارا بوو و {reward} پرسیارت زیادکرا.")
    else:
        bot.reply_to(message, f"❌ {reason}")

@bot.message_handler(commands=["credit"])
def cmd_credit(message):
    log_user(message)
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (message.from_user.id,)).fetchone()
    bot.reply_to(message, f"📊 پرسیارەکانی خەڵات: <b>{row[0] if row else 0}</b>")

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    log_user(message)
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    banned, until = check_ban(message.from_user.id)
    if banned and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, f"🚫 تۆ بلۆککراویت. کاتی کردنەوە: {until}")
        return
        
    set_state(message.from_user.id, "wait_lang")
    bot.reply_to(message, "📷 <b>وێنە وەرگیرا.</b>\nئێستا ناوی زمانەکە بنووسە: <code>HTML</code>, <code>CSS</code>, <code>JS</code>, <code>PHP</code>, <code>Python</code>.")

@bot.message_handler(func=lambda m: not m.text.startswith("/"), content_types=["text"])
def handle_text(message):
    log_user(message)
    
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    banned, until = check_ban(message.from_user.id)
    if banned and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, f"🚫 تۆ بلۆککراویت. کاتی کردنەوە: {until}")
        return

    uid = message.from_user.id
    q = message.text.strip()
    ql = q.lower()
    state, _ = get_state(uid)

    if state == "wait_lang":
        found_lang = None
        for k, v in LANG_MAP.items():
            if re.search(rf'\b{k}\b', ql):
                found_lang = v
                break
        if not found_lang:
            bot.reply_to(message, "❓ زمان نەناسرا. تکایە بنووسە: HTML، CSS، JS، PHP، Python یان React.")
            return
        clear_state(uid)
        code = _web_template(found_lang)
        safe_code = html.escape(code)
        
        # ئەمە ئەو دێڕەیە کە پێشتر لە کۆپیکردنەکەتدا ناتەواو مابووەوە
