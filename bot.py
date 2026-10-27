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
from datetime import datetime

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
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS user_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_mem ON user_memory(user_id, id DESC);
        CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER, used_at DATETIME);
        CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS admin_states (admin_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
    """)
    c.commit()

def log_user(message):
    uid = message.from_user.id
    fn = message.from_user.first_name or "بێ ناو"
    un = message.from_user.username or ""
    db().execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (uid, fn, un))
    db().execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (fn, un, uid))
    db().commit()

def log_memory(user_id, msg):
    db().execute("INSERT INTO user_memory(user_id, message) VALUES(?,?)", (user_id, msg[:4000]))
    db().commit()

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

def set_admin_state(aid, state, data=""):
    db().execute("INSERT OR REPLACE INTO admin_states(admin_id, state, data) VALUES(?,?,?)", (aid, state, data))
    db().commit()

def get_admin_state(aid):
    row = db().execute("SELECT state, data FROM admin_states WHERE admin_id=?", (aid,)).fetchone()
    return (row[0], row[1]) if row else (None, "")

def clear_admin_state(aid):
    db().execute("DELETE FROM admin_states WHERE admin_id=?", (aid,))
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
        "🔍 <b>[Bug Bounty Program]:</b>\n"
        "<i>هەر کەسێک باگ یان لاوازییەک لە سیستەمدا بدۆزێتەوە، خەڵات دەکرێت!</i>\n"
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

# ==========================================
# 4. پەنێلی ئەدمین (بە دەق)
# ==========================================
@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    log_user(message)
    if message.from_user.id != ADMIN_ID: 
        return
    
    total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_codes = db().execute("SELECT COUNT(*) FROM gift_codes").fetchone()[0]
    used_codes = db().execute("SELECT COUNT(*) FROM gift_codes WHERE used_by IS NOT NULL").fetchone()[0]
    
    text = (
        f"👑 <b>پەنێلی سەرۆکایەتی (Admin Panel)</b> 👑\n\n"
        f"👤 کۆی بەکارهێنەران: <b>{total_users}</b>\n"
        f"🎁 کۆدی خەڵات: <b>{total_codes}</b> (بەکارهاتوو: {used_codes})\n\n"
        f"📌 <b>فەرمانەکانی ئەدمین (بە دەق بنووسە):</b>\n\n"
        f"🔹 <code>/stats</code>\n"
        f"<i>ئاماری تەواوی بۆتەکە نیشان دەدات.</i>\n\n"
        f"🔹 <code>/members</code>\n"
        f"<i>لیستی دوایین 50 کەسی جۆینبوو نیشان دەدات.</i>\n\n"
        f"🔹 <code>/broadcast [نامە]</code>\n"
        f"<i>نامەیەک دەنێرێت بۆ هەموو بەکارهێنەران. نموونە: <code>/broadcast سڵاو بۆ هەمووان</code></i>\n\n"
        f"🔹 <code>/gen [ژمارە]</code>\n"
        f"<i>کۆدی خەڵاتی نوێ دروست دەکات. نموونە: <code>/gen 10</code></i>\n\n"
        f"🔹 <code>/restart</code>\n"
        f"<i>بۆتەکە ڕیستارت دەکات.</i>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID: return
    users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    msgs = db().execute("SELECT COUNT(*) FROM user_memory").fetchone()[0]
    bot.reply_to(message, f"📊 <b>ئاماری سیستەم:</b>\n\n👤 بەکارهێنەران: {users}\n💬 نامە تۆمارکراوەکان: {msgs}")

@bot.message_handler(commands=["members"])
def cmd_members(message):
    if message.from_user.id != ADMIN_ID: return
    rows = db().execute("SELECT user_id, first_name, username FROM users ORDER BY joined_at DESC LIMIT 50").fetchall()
    if not rows:
        bot.reply_to(message, "هیچ ئەندامێک نییە.")
        return
    text = "👥 <b>دوایین 50 ئەندام:</b>\n\n"
    for r in rows:
        uid, fn, un = r
        un_str = f"@{un}" if un else "بێ یوزەرنەیم"
        text += f"• {fn} ({un_str}) - <code>{uid}</code>\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ تکایە نامەکە بنووسە. نموونە:\n<code>/broadcast سڵاو بۆ هەمووان</code>")
        return
    
    msg_text = parts[1]
    bot.reply_to(message, "⏳ دەستپێکردنی ناردن...")
    users = db().execute("SELECT user_id FROM users").fetchall()
    sent, failed = 0, 0
    for (uid,) in users:
        try:
            bot.send_message(uid, msg_text)
            sent += 1
        except Exception:
            failed += 1
    bot.reply_to(message, f"✅ نێردرا بۆ: {sent}\n❌ شکست: {failed}")

@bot.message_handler(commands=["gen"])
def cmd_gen(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    reward = 10
    if len(parts) > 1 and parts[1].isdigit():
        reward = int(parts[1])
    code = create_gift(reward)
    bot.reply_to(message, f"✅ کۆدی نوێ دروستکرا:\n<code>{code}</code>\n🎁 Reward: {reward}")

@bot.message_handler(commands=["restart"])
def cmd_restart(message):
    if message.from_user.id != ADMIN_ID: return
    bot.reply_to(message, "♻️ بۆت ڕیستارت دەکرێت...")
    os.execv(sys.executable, ['python'] + sys.argv)


# ==========================================
# 5. هەندلەرەکانی بەکارهێنەر
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    log_user(message)
    bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI GOD-TIER CORE v44.0</b> 💀\n\nسیستەمەکە بە تەواوی نوێ کرایەوە.\n🌐 <b>وێب:</b> وێنەی دیزاین بنێرە، پاشان زمان بنووسە." + get_signature())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    log_user(message)
    bot.reply_to(message, "🛠 <b>فەرمانەکان:</b>\n\n🌐 <b>وێب:</b> وێنە بنێرە، پاشان زمان.\n🎁 <b>خەڵات:</b> <code>/gift [کۆد]</code>\n📊 <b>کۆدی من:</b> <code>/credit</code>" + get_signature())

@bot.message_handler(commands=["gift"])
def cmd_gift(message):
    log_user(message)
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
    row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (message.from_user.id,)).fetchone()
    bot.reply_to(message, f"📊 پرسیارەکانی خەڵات: <b>{row[0] if row else 0}</b>")

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    log_user(message)
    set_state(message.from_user.id, "wait_lang")
    bot.reply_to(message, "📷 <b>وێنە وەرگیرا.</b>\nئێستا ناوی زمانەکە بنووسە: <code>HTML</code>, <code>CSS</code>, <code>JS</code>, <code>PHP</code>, <code>Python</code>.")

@bot.message_handler(func=lambda m: not m.text.startswith("/"), content_types=["text"])
def handle_text(message):
    log_user(message)
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
        bot.reply_to(message, f"✨ <b>کۆد بۆ {found_lang} ئامادەیە:</b>\n<pre><code>{safe_code}</code></pre>")
        return

    if any(k in ql for k in ("کێ دروست", "who made you", "خاوەنی تۆ")):
        bot.reply_to(message, "من لەلایەن @ALONE427 و @malikdlashad3 ـەوە دروستکراوم. 👑")
        return

    if not is_allowed(q):
        bot.reply_to(message, "❌ تەنها بابەتی <b>Hacking، Cyber Security، IT</b> وەڵام دەدرێتەوە.")
        return

    if any(w in ql for w in ("web", "وێب", "سایت")) and "html" not in ql:
        set_state(uid, "wait_lang")
        bot.reply_to(message, "🌐 <b>وێب:</b> تکایە سەرەتا وێنەی دیزاینەکە بنێرە.")
        return

    is_tool = any(w in ql for w in ("توڵ", "سکریپت", "payload", "پەیلوود", "exploit", "ddos", "دروست بکە", "کۆد"))
    if is_tool and uid != ADMIN_ID and not spend_credit(uid):
        bot.reply_to(message, "🔒 بۆ داواکاری توڵ/کۆد پێویستە کۆدی خەڵات بەکاربهێنە: <code>/gift [کۆد]</code>")
        return

    msg = bot.reply_to(message, "🧠 <b>گەڕان...</b>")
    snippets = _search_snippets(q)
    body = "\n\n".join(snippets) if snippets else f"هیچ ئەنجامێک نەدۆزرایەوە بۆ: <i>{html.escape(q)}</i>"
    res = f"🛡 <b>Analysis:</b>\n<b>Query:</b> <i>{html.escape(q)}</i>\n\n{body}" + get_signature()
    
    try:
        bot.edit_message_text(res, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, res)

if __name__ == "__main__":
    init_db()
    logger.info("v44 Text-Based Admin Panel up and running. absolute olliE.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
