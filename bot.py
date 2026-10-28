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
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
DB_PATH = "bot_database.db"
AI_API_KEY = "AQ.Ab8RN6JwiCH_nK4jO18J2hjW267xM0uMs0TPRWnuZ1z0vmKV4A"
FORCE_CHANNEL = "@Nova_Kurd_Mod"  # کەناڵی ناچاری
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
            ban_until DATETIME DEFAULT NULL,
            refer_code TEXT,
            referred_by INTEGER,
            last_daily DATETIME DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS user_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_mem ON user_memory(user_id, id DESC);
        CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER, used_at DATETIME);
        CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task TEXT, status INTEGER DEFAULT 0);
    """)
    # زیادکردنی ستوونەکان ئەگەر پێشتر دروستکرابێت
    try: c.execute("ALTER TABLE users ADD COLUMN last_daily DATETIME DEFAULT NULL")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN refer_code TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except: pass
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
    c.commit()

def get_setting(key):
    row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, val):
    db().execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
    db().commit()

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
        INSERT OR IGNORE INTO users (user_id, first_name, username, phone, acc_created, refer_code) 
        VALUES (?, ?, ?, ?, datetime('now', 'localtime'), ?)
    """, (uid, fn, un, phone, f"ref_{uid}"))
    
    db().execute("""
        UPDATE users SET first_name=?, username=?, phone=? WHERE user_id=?
    """, (fn, un, phone, uid))
    db().commit()

def get_bot_status():
    return get_setting('bot_status') or "on"

def set_bot_status(status):
    set_setting('bot_status', status)

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
# 2. فەنکشنەکانی داتابەیس و کرێدیت
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

def set_credit(user_id, n):
    db().execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=?", (user_id, n, n))
    db().commit()

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
# 3. سیستەمی ناچاری جۆینبوون (Force Sub)
# ==========================================
def is_subscribed(user_id):
    """پشکنین ئەگەر بەکارهێنەر ئەندامی کەناڵەکەیە"""
    try:
        member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except ApiTelegramException as e:
        # ئەگەر بەکارهێنەر بە تەواوی نەدۆزرایەوە (هەرگیز جۆین نەبووە)
        logger.warning(f"Subscription check failed for {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False
    return False

def force_sub_msg(chat_id):
    """ناردنی نامەی ناچارکردن بە جۆینبوون"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 جۆینبوون بە کەناڵ", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("✅ پشکنین", callback_data="check_sub"))
    bot.send_message(
        chat_id, 
        "⚠️ <b>تکایە سەرەتا جۆین بە کەناڵەکە ببە بۆ ئەوەی بتوانیت بۆتەکە بەکاربهێنیت!</b>\n\n"
        "دوای جۆینبوون، کلیک لە دوگمەی 'پشکنین' بکە.", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ سوپاس بۆ جۆینبوون! ئێستا دەتوانیت بۆتەکە بەکاربهێنیت.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # ناردنی نامەی بەخێربێن
        bot.send_message(call.message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE v71.0</b> 💀\n\nسیستەمەکە بە تەواوی نوێ کرایەوە.\n🌐 <b>وێب:</b> وێنەی دیزاین بنێرە، یان لەبارەی تەکنەلۆجیا پرسیار بکە." + get_signature())
    else:
        bot.answer_callback_query(call.id, "❌ هێشتا جۆین نەبوویتە. تکایە سەرەتا جۆین ببە.", show_alert=True)

# ==========================================
# 4. مێشکی زیرەک
# ==========================================
def get_signature():
    return (
        "\n\n───────────────────\n"
        "🛡 <b>[BLACK HAT AI PRIME CORE]</b>\n"
        "🎁 بۆ بەکارهێنانی کۆدی خەڵات: <code>/gift [کۆد]</code>\n"
        "👑 <b>پەیوەندی:</b> @malikdlashad3 | @ALONE427"
    )

def get_prime_ai_response(query):
    if not AI_API_KEY: return "❌ کلیل نییە."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={AI_API_KEY}"
        prompt = (
            "You are BLACK HAT AI PRIME, an expert in technology, hacking, and programming. "
            "Answer in Kurdish Sorani, keep technical terms in English. Be precise and detailed. "
            f"User Question: {query}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
        return "❌ سیستەمی زیرەک نەیتوانی وەڵام بداتەوە."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "❌ کێشەیەک لە مێشکی سیستەم ڕوویدا."

def get_vision_ai_response(image_path, user_prompt):
    if not AI_API_KEY: return "❌ کلیل نییە."
    try:
        with open(image_path, "rb") as f:
            enc = base64.b64encode(f.read()).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={AI_API_KEY}"
        prompt = "You are an elite frontend developer. Write the complete HTML/CSS code for this UI image. " + user_prompt
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": enc}}]}]}
        response = requests.post(url, json=payload, timeout=45)
        data = response.json()
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
        return "❌ نەتوانرا وێنەکە بخوێنرێتەوە."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "❌ کێشەیەک لە سیستەمی بینین ڕوویدا."

# ==========================================
# 5. ئامێرەکان (Features)
# ==========================================
@bot.message_handler(commands=["qr"])
def cmd_qr(message):
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
    length = 16
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit(): length = min(int(parts[1]), 64)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    bot.reply_to(message, f"🔐 <b>پاسوۆردی بەهێز:</b>\n<code>{pwd}</code>")

@bot.message_handler(commands=["hash"])
def cmd_hash(message):
    text = message.text.replace("/hash", "").strip()
    if not text: return
    md5 = hashlib.md5(text.encode()).hexdigest()
    sha = hashlib.sha256(text.encode()).hexdigest()
    bot.reply_to(message, f"🔑 <b>MD5:</b>\n<code>{md5}</code>\n\n🔑 <b>SHA256:</b>\n<code>{sha}</code>")

@bot.message_handler(commands=["encode"])
def cmd_encode(message):
    text = message.text.replace("/encode", "").strip()
    if not text: return
    bot.reply_to(message, f"📦 <b>Base64:</b>\n<code>{base64.b64encode(text.encode()).decode()}</code>")

@bot.message_handler(commands=["decode"])
def cmd_decode(message):
    text = message.text.replace("/decode", "").strip()
    if not text: return
    try:
        dec = base64.b64decode(text.encode()).decode()
        bot.reply_to(message, f"📦 <b>Decoded:</b>\n<code>{dec}</code>")
    except: bot.reply_to(message, "❌ کۆدەکە هەڵەیە.")

@bot.message_handler(commands=["calc"])
def cmd_calc(message):
    expr = message.text.replace("/calc", "").strip()
    if not expr: return
    try:
        result = eval(expr, {"__builtins__": None}, {})
        bot.reply_to(message, f"🧮 <b>ئەنجام:</b> <code>{result}</code>")
    except: bot.reply_to(message, "❌ بیرکارییەکە هەڵەیە.")

@bot.message_handler(commands=["weather"])
def cmd_weather(message):
    city = message.text.replace("/weather", "").strip()
    if not city: return
    try:
        res = requests.get(f"https://wttr.in/{city}?format=3", timeout=10)
        bot.reply_to(message, f"🌤 <b>کەشوهەوا:</b>\n<code>{res.text}</code>")
    except: bot.reply_to(message, "❌ نەتوانرا کەشوهەوا بدۆزرێتەوە.")

@bot.message_handler(commands=["short"])
def cmd_short(message):
    url = message.text.replace("/short", "").strip()
    if not url: return
    try:
        res = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=10)
        bot.reply_to(message, f"🔗 <b>لینکی کورت:</b>\n{res.text}")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["dns"])
def cmd_dns(message):
    domain = message.text.replace("/dns", "").strip()
    if not domain: return
    try:
        ip = socket.gethostbyname(domain)
        bot.reply_to(message, f"🌐 <b>DNS Lookup:</b>\n<code>{domain}</code> → <code>{ip}</code>")
    except: bot.reply_to(message, "❌ نەتوانرا ئایپییەکە بدۆزرێتەوە.")

@bot.message_handler(commands=["whois"])
def cmd_whois(message):
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
    try:
        res = requests.get("https://meme-api.com/gimme/ProgrammerHumor", timeout=10).json()
        bot.send_photo(message.chat.id, res['url'], caption=f"😂 {res['title']}")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["quote"])
def cmd_quote(message):
    try:
        res = requests.get("https://zenquotes.io/api/random", timeout=10).json()
        bot.reply_to(message, f"💡 <i>\"{res[0]['q']}\"</i>\n\n— <b>{res[0]['a']}</b>")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["tr"])
def cmd_tr(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: return bot.reply_to(message, "⚠️ نموونە: <code>/tr en سڵاو</code>")
    lang, text = parts[1], parts[2]
    try:
        res = requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}", timeout=10).json()
        bot.reply_to(message, f"🌐 <b>وەرگێڕان:</b>\n{res[0][0][0]}")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["ud"])
def cmd_ud(message):
    term = message.text.replace("/ud", "").strip()
    if not term: return
    try:
        res = requests.get(f"http://api.urbandictionary.com/v0/define?term={urllib.parse.quote(term)}", timeout=10).json()
        if res['list']:
            d = res['list'][0]['definition'].replace('[', '').replace(']', '')
            bot.reply_to(message, f"📖 <b>{term}:</b>\n\n{d[:1000]}...")
        else: bot.reply_to(message, "❌ نەدۆزرایەوە.")
    except: bot.reply_to(message, "❌ هەڵە.")

@bot.message_handler(commands=["todo"])
def cmd_todo(message):
    parts = message.text.split(maxsplit=2)
    uid = message.from_user.id
    if len(parts) < 2:
        rows = db().execute("SELECT id, task, status FROM todos WHERE user_id=?", (uid,)).fetchall()
        if not rows: return bot.reply_to(message, "📝 لیستەکەت بەتاڵە.")
        txt = "📝 <b>لیستی کارەکانت:</b>\n\n"
        for r in rows: txt += f"{'✅' if r[2] else '⏳'} <code>{r[0]}</code>. {r[1]}\n"
        return bot.reply_to(message, txt + "\n<i>بۆ سڕینەوە: /todo del ID</i>")
    action = parts[1].lower()
    if action == "add" and len(parts) == 3:
        db().execute("INSERT INTO todos(user_id, task) VALUES(?,?)", (uid, parts[2]))
        db().commit()
        bot.reply_to(message, "✅ زیادکرا.")
    elif action == "del" and len(parts) == 3:
        db().execute("DELETE FROM todos WHERE id=? AND user_id=?", (parts[2], uid))
        db().commit()
        bot.reply_to(message, "🗑 سڕایەوە.")

@bot.message_handler(commands=["remind"])
def cmd_remind(message):
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

@bot.message_handler(commands=["referral"])
def cmd_referral(message):
    uid = message.from_user.id
    row = db().execute("SELECT refer_code FROM users WHERE user_id=?", (uid,)).fetchone()
    code = row[0] if row else f"ref_{uid}"
    link = f"https://t.me/{bot.get_me().username}?start={code}"
    bot.reply_to(message, f"👥 <b>سیستەمی بانگهێشتکردن:</b>\n\n🔗 لینکی تۆ:\n<code>{link}</code>\n\n<i>بۆ هەر هاوڕێیەک کە بانگهێشت بکەیت، 5 کرێدیت وەردەگریت.</i>")

@bot.message_handler(commands=["daily"])
def cmd_daily(message):
    uid = message.from_user.id
    row = db().execute("SELECT last_daily FROM users WHERE user_id=?", (uid,)).fetchone()
    now = datetime.now()
    if row and row[0]:
        last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if (now - last).total_seconds() < 86400:
            rem = 86400 - int((now - last).total_seconds())
            return bot.reply_to(message, f"⏳ چاوەڕوان بە. {rem // 3600} کاتژمێر و {(rem % 3600) // 60} خولەک ماوە.")
    add_credit(uid, 1)
    db().execute("UPDATE users SET last_daily=datetime('now', 'localtime') WHERE user_id=?", (uid,))
    db().commit()
    bot.reply_to(message, "🎁 <b>پیرۆزە!</b> 1 کرێدیتی ڕۆژانە زیادکرا." + get_signature())

@bot.message_handler(commands=["profile"])
def cmd_profile(message):
    uid = message.from_user.id
    u = db().execute("SELECT first_name, joined_at FROM users WHERE user_id=?", (uid,)).fetchone()
    c = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (uid,)).fetchone()
    m = db().execute("SELECT COUNT(*) FROM user_memory WHERE user_id=?", (uid,)).fetchone()[0]
    bot.reply_to(message, f"👤 <b>پرۆفایل:</b>\n🆔 <code>{uid}</code>\n📅 جۆینبوون: {u[1] if u else '?'}\n💳 کرێدیت: <b>{c[0] if c else 0}</b>\n💬 نامەکان: {m}" + get_signature())

@bot.message_handler(commands=["top"])
def cmd_top(message):
    rows = db().execute("SELECT u.first_name, c.questions_left FROM credit c JOIN users u ON c.user_id = u.user_id ORDER BY c.questions_left DESC LIMIT 10").fetchall()
    txt = "🏆 <b>باشترین 10 بەکارهێنەر:</b>\n\n"
    for i, r in enumerate(rows, 1): txt += f"{i}. {r[0]} — <b>{r[1]}</b> کرێدیت\n"
    bot.reply_to(message, txt + get_signature())

@bot.message_handler(commands=["ping"])
def cmd_ping(message):
    start = time.time()
    msg = bot.reply_to(message, "🏓...")
    bot.edit_message_text(f"🏓 پۆنگ! {round((time.time() - start) * 1000)}ms", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=["time"])
def cmd_time(message):
    bot.reply_to(message, f"⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>")

# ==========================================
# 6. پەنێلی ئەدمین
# ==========================================
@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if message.from_user.id != ADMIN_ID: return
    total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_codes = db().execute("SELECT COUNT(*) FROM gift_codes").fetchone()[0]
    bot_status = get_bot_status()
    
    text = (
        f"👑 <b>پەنێلی سەرۆکایەتی (Admin Panel) — v71.0</b> 👑\n\n"
        f"👤 بەکارهێنەران: <b>{total_users}</b>\n"
        f"🎁 کۆدەکان: <b>{total_codes}</b>\n"
        f"⚙️ دۆخی بۆت: <b>{'✅ کارا' if bot_status == 'on' else '❌ ناچالاک'}</b>\n"
        f"📢 کەناڵی ناچاری: <b>{FORCE_CHANNEL}</b>\n\n"
        f"📌 <b>فەرمانەکان:</b>\n"
        f"🔹 <code>/stats</code> | <code>/members</code> | <code>/user [ID]</code>\n"
        f"🔹 <code>/send [ID] [نامە]</code> | <code>/broadcast [نامە]</code>\n"
        f"🔹 <code>/addcredit</code> | <code>/remcredit</code> | <code>/setcredit</code>\n"
        f"🔹 <code>/ban [ID] [کات]</code> | <code>/unban [ID]</code>\n"
        f"🔹 <code>/on</code> | <code>/off</code> | <code>/gen</code> | <code>/codes</code>\n"
        f"🔹 <code>/backup</code> | <code>/resetdaily [ID]</code>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["resetdaily"])
def cmd_reset_daily(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2: return
    db().execute("UPDATE users SET last_daily=NULL WHERE user_id=?", (parts[1],))
    db().commit()
    bot.reply_to(message, "✅ ڕیستارت کرا.")

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID: return
    u = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    b = db().execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
    m = db().execute("SELECT COUNT(*) FROM user_memory").fetchone()[0]
    bot.reply_to(message, f"📊 بەکارهێنەران: {u}\n🚫 بلۆککراو: {b}\n💬 نامەکان: {m}")

@bot.message_handler(commands=["members"])
def cmd_members(message):
    if message.from_user.id != ADMIN_ID: return
    rows = db().execute("SELECT user_id, first_name, is_banned FROM users ORDER BY joined_at DESC LIMIT 50").fetchall()
    txt = "👥 <b>50 ئەندامی کۆتایی:</b>\n\n"
    for r in rows: txt += f"{'🚫' if r[2] else '✅'} {r[1]} - <code>{r[0]}</code>\n"
    bot.reply_to(message, txt)

@bot.message_handler(commands=["user"])
def cmd_user_info(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split()
    if len(parts) < 2: return
    r = db().execute("SELECT user_id, first_name, username, phone, acc_created, joined_at, is_banned, ban_until FROM users WHERE user_id=?", (parts[1],)).fetchone()
    if not r: return bot.reply_to(message, "❌ نەدۆزرایەوە.")
    st = "✅ ئاسایی" if not r[6] else f"🚫 بلۆک (تا: {r[7]})"
    bot.reply_to(message, f"👤 <b>زانیاری:</b>\n🆔 <code>{r[0]}</code>\n📝 ناو: {r[1]}\n🔗 یوزەر: @{r[2]}\n📞 تەلەفۆن: {r[3]}\n📅 ئەکاونت: {r[4]}\n📥 جۆینبوون: {r[5]}\n⚙️ دۆخ: {st}")

@bot.message_handler(commands=["send"])
def cmd_send(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: return
    try:
        bot.send_message(int(parts[1]), parts[2])
        bot.reply_to(message, "✅ نێردرا.")
    except Exception as e: bot.reply_to(message, f"❌ هەڵە: {e}")

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return
    users = db().execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    s, f = 0, 0
    for (uid,) in users:
        try:
            bot.send_message(uid, parts[1])
            s += 1
            time.sleep(0.05)
        except: f += 1
    bot.reply_to(message, f"✅ نێردرا: {s} | ❌ شکست: {f}")

@bot.message_handler(commands=["addcredit"])
def cmd_add_credit(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 3: return
    add_credit(int(p[1]), int(p[2]))
    bot.reply_to(message, f"✅ {p[2]} کرێدیت زیادکرا.")

@bot.message_handler(commands=["remcredit"])
def cmd_remove_credit(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 3: return
    remove_credit(int(p[1]), int(p[2]))
    bot.reply_to(message, f"✅ {p[2]} کرێدیت کەمکرایەوە.")

@bot.message_handler(commands=["setcredit"])
def cmd_set_credit(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 3: return
    set_credit(int(p[1]), int(p[2]))
    bot.reply_to(message, f"✅ کرێدیت کرا بە {p[2]}.")

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return
    t_id = int(p[1])
    t_str = p[2] if len(p) > 2 else "0"
    if t_id == ADMIN_ID: return bot.reply_to(message, "❌ خۆت ناتوانیت بلۆک بکەیت.")
    b_until = parse_ban_time(t_str)
    if b_until is False: return bot.reply_to(message, "❌ کات هەڵەیە.")
    if b_until is None:
        db().execute("UPDATE users SET is_banned=1, ban_until=NULL WHERE user_id=?", (t_id,))
        bot.reply_to(message, "🚫 بۆ هەتا هەتای بلۆک کرا.")
    else:
        db().execute("UPDATE users SET is_banned=1, ban_until=? WHERE user_id=?", (b_until, t_id))
        bot.reply_to(message, f"🚫 تا {b_until} بلۆک کرا.")
    db().commit()

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return
    db().execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (int(p[1]),))
    db().commit()
    bot.reply_to(message, "✅ کرایەوە.")

@bot.message_handler(commands=["on"])
def cmd_on(message):
    if message.from_user.id != ADMIN_ID: return
    set_bot_status("on")
    bot.reply_to(message, "✅ کارا کرا.")

@bot.message_handler(commands=["off"])
def cmd_off(message):
    if message.from_user.id != ADMIN_ID: return
    set_bot_status("off")
    bot.reply_to(message, "❌ ناچالاک کرا.")

@bot.message_handler(commands=["gen"])
def cmd_gen(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    rew = int(p[1]) if len(p) > 1 and p[1].isdigit() else 10
    c = create_gift(rew)
    bot.reply_to(message, f"✅ کۆد: <code>{c}</code>")

@bot.message_handler(commands=["codes"])
def cmd_codes(message):
    if message.from_user.id != ADMIN_ID: return
    rows = db().execute("SELECT code, reward FROM gift_codes WHERE used_by IS NULL ORDER BY rowid DESC LIMIT 10").fetchall()
    txt = "🎁 <b>کۆدە چالاکەکان:</b>\n\n"
    for r in rows: txt += f"🔹 <code>{r[0]}</code> (پرسیار: {r[1]})\n"
    bot.reply_to(message, txt)

@bot.message_handler(commands=["delcode"])
def cmd_del_code(message):
    if message.from_user.id != ADMIN_ID: return
    p = message.text.split()
    if len(p) < 2: return
    db().execute("DELETE FROM gift_codes WHERE code=?", (p[1],))
    db().commit()
    bot.reply_to(message, "✅ سڕایەوە.")

@bot.message_handler(commands=["clearcodes"])
def cmd_clear_codes(message):
    if message.from_user.id != ADMIN_ID: return
    db().execute("DELETE FROM gift_codes WHERE used_by IS NULL")
    db().commit()
    bot.reply_to(message, "✅ هەموو کۆدەکان سڕانەوە.")

@bot.message_handler(commands=["backup"])
def cmd_backup(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        with open(DB_PATH, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📁 <b>Backup Database</b>")
    except Exception as e: bot.reply_to(message, f"❌ هەڵە: {e}")

# ==========================================
# 7. هەندلەرەکانی سەرەکی (بەکارهێنەر)
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    log_user(message)
    
    # پشکنینی ریفێراڵ
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].replace("ref_", ""))
            if ref_id != message.from_user.id:
                row = db().execute("SELECT referred_by FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
                if row and row[0] is None:
                    db().execute("UPDATE users SET referred_by=? WHERE user_id
