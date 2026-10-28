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
import requests
import time
import base64
import hashlib
import string
import socket
import io
import qrcode
from datetime import datetime, timedelta

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# ==========================================
# 1. کۆنفیگەرەیشن (ڕێکخستنەکان)
# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
DB_PATH = "bot_database.db"
AI_API_KEY = "AQ.Ab8RN6JwiCH_nK4jO18J2hjW267xM0uMs0TPRWnuZ1z0vmKV4A"
FORCE_CHANNEL = "@Nova_Kurd_Mod"

# ==========================================
# 2. ڕێکخستنی لۆگ و بۆت
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("UltimateGodTierCore")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================================
# 3. داتابەیس (SQLite)
# ==========================================
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            ban_until DATETIME DEFAULT NULL,
            refer_code TEXT,
            referred_by INTEGER,
            last_daily DATETIME DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS simple_admins (user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            message TEXT, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            role TEXT, 
            content TEXT, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY, 
            reward INTEGER DEFAULT 10, 
            used_by INTEGER, 
            used_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS credit (
            user_id INTEGER PRIMARY KEY, 
            questions_left INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            task TEXT, 
            status INTEGER DEFAULT 0
        );
    """)
    # دڵنیابوونە لەوەی کۆڵۆنە نوێیەکان زیادکراون
    try: c.execute("ALTER TABLE users ADD COLUMN last_daily DATETIME DEFAULT NULL")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN last_seen DATETIME DEFAULT CURRENT_TIMESTAMP")
    except: pass
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.commit()
    c.close()

# ==========================================
# 4. فەنکشنەکانی یارمەتیدەر
# ==========================================
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
    c.close()
    return is_new_user

def is_simple_admin(uid):
    c = db()
    row = c.execute("SELECT user_id FROM simple_admins WHERE user_id=?", (uid,)).fetchone()
    c.close()
    return row is not None

def get_bot_status():
    c = db()
    row = c.execute("SELECT value FROM settings WHERE key='bot_status'").fetchone()
    c.close()
    return row[0] if row else "on"

def set_bot_status(status):
    c = db()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (status,))
    c.commit()
    c.close()

def add_credit(user_id, n):
    c = db()
    c.execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=questions_left+?", (user_id, n, n))
    c.commit()
    c.close()

def spend_credit(user_id):
    if user_id == ADMIN_ID or is_simple_admin(user_id):
        return True # بێکۆتا
    c = db()
    row = c.execute("SELECT questions_left FROM credit WHERE user_id=?", (user_id,)).fetchone()
    if row and row[0] > 0:
        c.execute("UPDATE credit SET questions_left=questions_left-1 WHERE user_id=?", (user_id,))
        c.commit()
        c.close()
        return True
    c.close()
    return False

def get_credit(uid):
    if uid == ADMIN_ID or is_simple_admin(uid): 
        return "♾️ بێکۆتایی"
    c = db()
    row = c.execute("SELECT questions_left FROM credit WHERE user_id=?", (uid,)).fetchone()
    c.close()
    return str(row[0]) if row else "0"

def check_ban(uid):
    c = db()
    row = c.execute("SELECT is_banned, ban_until FROM users WHERE user_id=?", (uid,)).fetchone()
    c.close()
    if not row or row[0] == 0: return False, None
    ban_until = row[1]
    if ban_until is None: return True, "هەتا هەتای"
    try:
        now = datetime.now()
        until = datetime.strptime(ban_until, "%Y-%m-%d %H:%M:%S")
        if now > until:
            c = db()
            c.execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (uid,))
            c.commit()
            c.close()
            return False, None
        return True, ban_until
    except ValueError:
        return False, None

def parse_ban_time(time_str):
    time_str = time_str.lower().strip()
    if time_str == "0": return None
    match = re.match(r'^(\d+)([mhdw]|mo)$', time_str)
    if not match: return False
    val = int(match.group(1))
    unit = match.group(2)
    now = datetime.now()
    if unit == 'm': return (now + timedelta(minutes=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'h': return (now + timedelta(hours=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'd': return (now + timedelta(days=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'w': return (now + timedelta(weeks=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'mo': return (now + timedelta(days=val*30)).strftime("%Y-%m-%d %H:%M:%S")
    return False

# ==========================================
# 5. سیستەمی مێشکی زیرەک (Gemini AI)
# ==========================================
def get_ai_response(user_id, query):
    if not AI_API_KEY: return "❌ کلیل نییە."
    try:
        c = db()
        history = c.execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 6", (user_id,)).fetchall()
        c.close()
        history.reverse()
        
        contents = [{"role": role, "parts": [{"text": content}]} for role, content in history]
        contents.append({"role": "user", "parts": [{"text": query}]})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={AI_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": "You are BLACK HAT AI PRIME. Reply in the exact same language the user used. Be incredibly precise and detailed."}]},
            "contents": contents
        }
        res = requests.post(url, json=payload, timeout=40).json()
        
        if 'candidates' in res and len(res['candidates']) > 0:
            ai_text = res['candidates'][0]['content']['parts'][0]['text']
            c = db()
            c.execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "user", query))
            c.execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "model", ai_text))
            c.commit()
            c.close()
            return ai_text
        return "❌ سیستەمی زیرەک وەڵامی نەدایەوە."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "❌ کێشەیەک لە مێشکی سیستەم ڕوویدا."

def get_vision_ai_response(image_path, user_prompt):
    if not AI_API_KEY: return "❌ کلیل نییە."
    try:
        with open(image_path, "rb") as f: 
            enc = base64.b64encode(f.read()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={AI_API_KEY}"
        prompt = "You are an elite frontend developer. Write the complete HTML/CSS code for this UI image. " + user_prompt
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": enc}}]}]}
        res = requests.post(url, json=payload, timeout=45).json()
        if 'candidates' in res and len(res['candidates']) > 0:
            return res['candidates'][0]['content']['parts'][0]['text']
        return "❌ نەتوانرا وێنەکە بخوێنرێتەوە."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "❌ کێشەیەک لە سیستەمی بینین ڕوویدا."

# ==========================================
# 6. پشکنینی جۆینبوون بە کەناڵ
# ==========================================
def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']: return True
    except Exception:
        return False
    return False

def force_sub_msg(chat_id):
    markup = types.InlineKeyboardMarkup()
    url = f"https://t.me/{FORCE_CHANNEL.replace('@', '')}"
    markup.add(types.InlineKeyboardButton("📢 جۆینبوون بە کەناڵ", url=url))
    markup.add(types.InlineKeyboardButton("✅ پشکنین", callback_data="check_sub"))
    msg_text = (
        "⚠️ <b>تکایە سەرەتا جۆین بە کەناڵەکە ببە بۆ ئەوەی بتوانیت بۆتەکە بەکاربهێنیت!</b>\n\n"
        "دوای جۆینبوون، کلیک لە دوگمەی 'پشکنین' بکە."
    )
    bot.send_message(chat_id, msg_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ سوپاس بۆ جۆینبوون!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE</b> 💀\n\nسیستەمەکە ئامادەیە.\n🌐 وێنە بنێرە یان پرسیار بکە.")
    else:
        bot.answer_callback_query(call.id, "❌ هێشتا جۆین نەبوویتە.", show_alert=True)

# ==========================================
# 7. فەرمانەکانی ئەدمینی سەرەکی
# ==========================================
@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if message.from_user.id != ADMIN_ID: return
    total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    text = (
        f"👑 <b>پەنێلی سەرۆکایەتی</b>\n\n"
        f"👤 بەکارهێنەران: {total_users}\n\n"
        f"📌 <b>فەرمانەکان:</b>\n"
        f"🔹 <code>/addsimple [ID]</code> — ئەدمینی سادە (بێکۆتا)\n"
        f"🔹 <code>/removesimple [ID]</code> — لابردنی ئەدمین\n"
        f"🔹 <code>/addcredit [ID] [ژمارە]</code>\n"
        f"🔹 <code>/gen [ژمارە]</code> — کۆدی خەڵات\n"
        f"🔹 <code>/broadcast [نامە]</code>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["addsimple"])
def cmd_add_simple(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "⚠️ نموونە: <code>/addsimple 123456789</code>")
    c = db()
    c.execute("INSERT OR IGNORE INTO simple_admins(user_id) VALUES(?)", (int(parts[1]),))
    c.commit()
    c.close()
    bot.reply_to(message, f"✅ بەکارهێنەر <code>{parts[1]}</code> کرا بە ئەدمینی سادە (کرێدیتی بێکۆتایە، بەڵام دەسەڵاتی ئەدمینی نییە).")

@bot.message_handler(commands=["removesimple"])
def cmd_remove_simple(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2: return
    c = db()
    c.execute("DELETE FROM simple_admins WHERE user_id=?", (int(parts[1]),))
    c.commit()
    c.close()
    bot.reply_to(message, f"✅ ئەدمینی سادە لابرا.")

@bot.message_handler(commands=["addcredit"])
def cmd_add_credit(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 3: return
    add_credit(int(p[1]), int(p[2]))
    bot.reply_to(message, f"✅ {p[2]} کرێدیت زیادکرا.")

@bot.message_handler(commands=["gen"])
def cmd_gen(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    rew = int(p[1]) if len(p) > 1 and p[1].isdigit() else 10
    code = f"BUGFIX-{random.randint(1000, 9999)}-{random.choice('XZKM')}{random.randint(100, 999)}"
    c = db()
    c.execute("INSERT INTO gift_codes(code, reward) VALUES(?,?)", (code, rew))
    c.commit()
    c.close()
    bot.reply_to(message, f"✅ کۆد: <code>{code}</code>")

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return
    c = db()
    users = c.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    c.close()
    s, f = 0, 0
    for (uid,) in users:
        try:
            bot.send_message(uid, parts[1])
            s += 1
            time.sleep(0.05)
        except: f += 1
    bot.reply_to(message, f"✅ نێردرا: {s} | ❌ شکست: {f}")

# ==========================================
# 8. فەرمانەکانی بەکارهێنەر
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not is_subscribed(message.from_user.id):
        return force_sub_msg(message.chat.id)
        
    is_new = log_user(message)
    if is_new:
        add_credit(message.from_user.id, 5)
        bot.send_message(message.chat.id, "🎁 <b>پیرۆزە!</b> 5 کرێدیت بەخۆڕایی وەک دیاری یەکەم جار زیادکرا.")
        
    bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE v80</b> 💀\n\nسیستەمەکە ئامادەیە.\n🌐 وێنە بنێرە یان پرسیار بکە.")

@bot.message_handler(commands=["credit"])
def cmd_credit(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    bot.reply_to(message, f"💳 کرێدیت: <b>{get_credit(message.from_user.id)}</b>")

@bot.message_handler(commands=["daily"])
def cmd_daily(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    log_user(message)
    uid = message.from_user.id
    if uid == ADMIN_ID or is_simple_admin(uid):
        return bot.reply_to(message, "💳 تۆ ئەدمینیت، کرێدیتت بێکۆتایە.")
        
    c = db()
    row = c.execute("SELECT last_daily FROM users WHERE user_id=?", (uid,)).fetchone()
    now = time.time()
    if row and row[0]:
        try:
            last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp()
            if now - last < 86400:
                rem = 86400 - int(now - last)
                c.close()
                return bot.reply_to(message, f"⏳ چاوەڕوان بە. {rem // 3600} کاتژمێر و {(rem % 3600) // 60} خولەک ماوە.")
        except ValueError: pass
            
    add_credit(uid, 1)
    c.execute("UPDATE users SET last_daily=datetime('now', 'localtime') WHERE user_id=?", (uid,))
    c.commit()
    c.close()
    bot.reply_to(message, "🎁 <b>پیرۆزە!</b> 1 کرێدیتی ڕۆژانە وەرگیرا.")

@bot.message_handler(commands=["gift"])
def cmd_gift(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "🎁 کۆدەکە بنووسە.")
    
    c = db()
    row = c.execute("SELECT used_by, reward FROM gift_codes WHERE code=?", (parts[1].strip(),)).fetchone()
    if not row: 
        c.close()
        return bot.reply_to(message, "❌ کۆدی نەناسراو.")
    if row[0] is not None: 
        c.close()
        return bot.reply_to(message, "❌ ئەم کۆدە پێشتر بەکارهاتووە.")
        
    c.execute("UPDATE gift_codes SET used_by=?, used_at=CURRENT_TIMESTAMP WHERE code=?", (message.from_user.id, parts[1]))
    c.commit()
    c.close()
    add_credit(message.from_user.id, row[1])
    bot.reply_to(message, f"🎉 پیرۆزە! {row[1]} کرێدیت زیادکرا.")

@bot.message_handler(commands=["profile"])
def cmd_profile(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    uid = message.from_user.id
    c = db()
    u = c.execute("SELECT first_name, joined_at FROM users WHERE user_id=?", (uid,)).fetchone()
    c.close()
    bot.reply_to(message, f"👤 <b>پرۆفایل:</b>\n🆔 <code>{uid}</code>\n📅 جۆینبوون: {u[1] if u else '?'}\n💳 کرێدیت: <b>{get_credit(uid)}</b>")

# ==========================================
# 9. ئامێرەکان (Tools)
# ==========================================
@bot.message_handler(commands=["qr"])
def cmd_qr(message):
    if not is_subscribed(message.from_user.id): return
    text = message.text.replace("/qr", "").strip()
    if not text: return bot.reply_to(message, "⚠️ نموونە: <code>/qr https://google.com</code>")
    img = qrcode.make(text)
    bio = io.BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    bot.send_photo(message.chat.id, bio, caption="✅ QR Code ئامادەیە.")

@bot.message_handler(commands=["pass"])
def cmd_pass(message):
    if not is_subscribed(message.from_user.id): return
    length = 16
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit(): length = min(int(parts[1]), 64)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    bot.reply_to(message, f"🔐 <b>پاسوۆردی بەهێز:</b>\n<code>{pwd}</code>")

@bot.message_handler(commands=["hash"])
def cmd_hash(message):
    if not is_subscribed(message.from_user.id): return
    text = message.text.replace("/hash", "").strip()
    if not text: return
    md5 = hashlib.md5(text.encode()).hexdigest()
    sha = hashlib.sha256(text.encode()).hexdigest()
    bot.reply_to(message, f"🔑 <b>MD5:</b>\n<code>{md5}</code>\n\n🔑 <b>SHA256:</b>\n<code>{sha}</code>")

@bot.message_handler(commands=["calc"])
def cmd_calc(message):
    if not is_subscribed(message.from_user.id): return
    expr = message.text.replace("/calc", "").strip()
    if not expr: return
    try:
        result = eval(expr, {"__builtins__": None}, {})
        bot.reply_to(message, f"🧮 <b>ئەنجام:</b> <code>{result}</code>")
    except: bot.reply_to(message, "❌ بیرکارییەکە هەڵەیە.")

@bot.message_handler(commands=["weather"])
def cmd_weather(message):
    if not is_subscribed(message.from_user.id): return
    city = message.text.replace("/weather", "").strip()
    if not city: return
    try:
        res = requests.get(f"https://wttr.in/{city}?format=3", timeout=10)
        bot.reply_to(message, f"🌤 <b>کەشوهەوا:</b>\n<code>{res.text}</code>")
    except: bot.reply_to(message, "❌ نەتوانرا کەشوهەوا بدۆزرێتەوە.")

@bot.message_handler(commands=["dns"])
def cmd_dns(message):
    if not is_subscribed(message.from_user.id): return
    domain = message.text.replace("/dns", "").strip()
    if not domain: return
    try:
        ip = socket.gethostbyname(domain)
        bot.reply_to(message, f"🌐 <b>DNS Lookup:</b>\n<code>{domain}</code> → <code>{ip}</code>")
    except: bot.reply_to(message, "❌ نەتوانرا ئایپییەکە بدۆزرێتەوە.")

@bot.message_handler(commands=["whois"])
def cmd_whois(message):
    if not is_subscribed(message.from_user.id): return
    domain = message.text.replace("/whois", "").strip()
    if not domain: return
    try:
        res = requests.get(f"https://rdap.org/domain/{domain}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            reg_date = next((ev.get('eventDate') for ev in data.get('events', []) if ev.get('eventAction') == 'registration'), 'نەزانراو')
            bot.reply_to(message, f"🌐 <b>WHOIS:</b> {domain}\n📅 <b>تۆمارکردن:</b> {reg_date}")
        else: bot.reply_to(message, "❌ نەدۆزرایەوە.")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["ip"])
def cmd_ip(message):
    if not is_subscribed(message.from_user.id): return
    ip = message.text.replace("/ip", "").strip()
    if not ip: return
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,query", timeout=10).json()
        if res['status'] == 'success':
            bot.reply_to(message, f"🌍 <b>IP:</b> {res['query']}\n🏳️ <b>وڵات:</b> {res['country']}\n🏙 <b>شار:</b> {res['city']}\n🏢 <b>ISP:</b> {res['isp']}")
        else: bot.reply_to(message, "❌ هەڵە.")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["meme"])
def cmd_meme(message):
    if not is_subscribed(message.from_user.id): return
    try:
        res = requests.get("https://meme-api.com/gimme/ProgrammerHumor", timeout=10).json()
        bot.send_photo(message.chat.id, res['url'], caption=f"😂 {res['title']}")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["tr"])
def cmd_tr(message):
    if not is_subscribed(message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: return bot.reply_to(message, "⚠️ نموونە: <code>/tr en سڵاو</code>")
    lang, text = parts[1], parts[2]
    try:
        res = requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}", timeout=10).json()
        bot.reply_to(message, f"🌐 <b>وەرگێڕان:</b>\n{res[0][0][0]}")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["remind"])
def cmd_remind(message):
    if not is_subscribed(message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: return bot.reply_to(message, "⚠️ نموونە: <code>/remind 10m کۆفی</code>")
    time_str, text = parts[1], parts[2]
    val = int(re.findall(r'\d+', time_str)[0]) if re.findall(r'\d+', time_str) else 0
    unit = time_str[-1]
    seconds = val * 60 if unit == 'm' else val * 3600 if unit == 'h' else val
    uid = message.from_user.id
    bot.reply_to(message, f"⏰ باشە، دوای {time_str} بیرت دەخەمەوە.")
    def remind():
        time.sleep(seconds)
        bot.send_message(uid, f"🔔 <b>بیرخستنەوە:</b>\n{text}")
    threading.Thread(target=remind, daemon=True).start()

# ==========================================
# 10. وەڵامدانەوەی نامەکان و وێنەکان (AI)
# ==========================================
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    if message.from_user.id != ADMIN_ID and not spend_credit(message.from_user.id):
        return bot.reply_to(message, "🔒 کرێدیتت نییە. بە <code>/daily</code> وەریبگرە.")
        
    bot.send_chat_action(message.chat.id, 'typing')
    msg = bot.reply_to(message, "👁 <b>سیستەمی بینین وێنەکە دەخوێنێتەوە...</b>")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    with open("temp.jpg", 'wb') as new_file: new_file.write(downloaded)
    ai_res = get_vision_ai_response("temp.jpg", message.caption or "")
    safe_text = ai_res.replace('<', '&lt;').replace('>', '&gt;')
    res = f"<pre><code>{safe_text[:3800]}</code></pre>"
    
    try: bot.edit_message_text(res, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
    except: bot.send_message(message.chat.id, res)
    if os.path.exists("temp.jpg"): os.remove("temp.jpg")

@bot.message_handler(func=lambda m: not m.text.startswith("/"), content_types=["text"])
def handle_text(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    if message.from_user.id != ADMIN_ID and get_bot_status() == "off": return
    
    banned, until = check_ban(message.from_user.id)
    if banned and message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, f"🚫 بلۆککراویت. تا: {until}")

    uid = message.from_user.id
    q = message.text.strip()
    ql = q.lower()

    if any(k in ql for k in ("کێ دروست", "who made you")):
        return bot.reply_to(message, "من لەلایەن @ALONE427 و @malikdlashad3 ـەوە دروستکراوم. 👑")
        
    if any(k in ql for k in ("سڵاو", "hello", "hi", "hey")):
        return bot.reply_to(message, "سڵاو بەخێربێیت. چۆن دەتوانم یارمەتیت بدەم؟")

    if uid != ADMIN_ID and not spend_credit(uid):
        return bot.reply_to(message, "🔒 کرێدیتت نییە. بە <code>/daily</code> وەریبگرە.")

    bot.send_chat_action(message.chat.id, 'typing')
    msg = bot.reply_to(message, "🧠 <b>سیستەمی زیرەک شیکاری دەکات...</b>")
    ai_response = get_ai_response(uid, q)
    
    safe_ai_text = ai_response.replace('<', '&lt;').replace('>', '&gt;')
    if len(safe_ai_text) > 3800:
        chunks = [safe_ai_text[i:i+3800] for i in range(0, len(safe_ai_text), 3800)]
        try: bot.edit_message_text(f"{chunks[0]}", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        except: bot.send_message(message.chat.id, f"{chunks[0]}", parse_mode="HTML")
        for chunk in chunks[1:]:
            time.sleep(0.5)
            bot.send_message(message.chat.id, chunk, parse_mode="HTML")
    else:
        try: bot.edit_message_text(f"{safe_ai_text}", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        except: bot.send_message(message.chat.id, f"{safe_ai_text}", parse_mode="HTML")

# ==========================================
# 11. ڕەنکردنی بۆت
# ==========================================
if __name__ == "__main__":
    init_db()
    logger.info("System is up and running. absolute olliE.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
