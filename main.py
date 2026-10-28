#!/usr/bin/env python3
"""
BLACK HAT AI PRIME — Complete Single-File Bot
Features: Bilingual (KU/EN), Credits System, Admin Panel, Footer, HTML Safe.
"""

import os
import sys
import time
import html
import base64
import sqlite3
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

# Optional .env loader
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import telebot
from telebot import types
from openai import OpenAI

# ==========================================
# 1. CONFIGURATION
# ==========================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ku").strip().lower()

# Admins
ADMIN_IDS = {5527152252, 8487940066}

# Limits & Systems
STARTING_CREDITS = 5
DAILY_CREDITS = 1
DAILY_CAP_DAYS = 30
MAX_INPUT_CHARS = 4000
MAX_IMAGE_BYTES = 15_000_000
MAX_OUTPUT_TOKENS = 1800
HISTORY_LIMIT = 12
MAX_HISTORY_ROWS = 100
RATE_LIMIT_PER_MINUTE = 30

SYSTEM_PROMPT = (
    "You are BLACK HAT AI PRIME, a helpful multilingual assistant. "
    "You understand Sorani Kurdish and answer in the language the user uses. "
    "Be direct, accurate, and complete. Never invent facts."
)

if not BOT_TOKEN:
    sys.exit("FATAL: missing TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    sys.exit("FATAL: missing OPENAI_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("BlackHatPrime")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0, max_retries=2)

_recent_requests = {}
_recent_lock = threading.Lock()

# ==========================================
# 2. STATIC MESSAGES (FOOTER & SYSTEM)
# ==========================================

FOOTER_KU = (
    "\n\n─────────────\n"
    "📖 <b>ڕێنمای بەکارهێنان</b>\n"
    "• نامەیەک بنێرە بۆ دروستکردنی توڵ (١ کرێدیت)\n"
    "• ڕۆژانە ١ کرێدیت زیاد دەبێت\n"
    "• /start — بینینی کرێدیتی خۆت\n\n"
    "🏆 <b>پاداشت:</b> هەر کەسێک کێشەیەک لە بۆت بدۆزێتەوە، خەڵات دەکرێت\n\n"
    "👤 <b>خاوەنەکان:</b> @ALONE427 @malikdlashad3"
)

FOOTER_EN = (
    "\n\n─────────────\n"
    "📖 <b>Usage guide</b>\n"
    "• Send a message to build a tool (1 credit)\n"
    "• +1 credit per day\n"
    "• /start — view your credits\n\n"
    "🏆 <b>Reward:</b> Anyone who finds a bug in the bot is rewarded\n\n"
    "👤 <b>Owners:</b> @ALONE427 @malikdlashad3"
)

def get_footer(lang):
    return FOOTER_KU if lang == "ku" else FOOTER_EN

# ==========================================
# 3. REPLY BANK (BILINGUAL - FULL RESTORED)
# ==========================================

BANK = {
    "ku": {
        "welcome": [
            "سڵاو {name}! بەخێربێیت بۆ <b>BLACK HAT AI PRIME</b>.\n\n• نامە بنێرە بۆ گفتوگۆ.\n• وێنە بنێرە بۆ شیکردنەوە.\n• /lang ku|en بۆ گۆڕینی زمان.",
            "بەخێربێی {name}! ئامادەیم. نامەیەک بنێرە یان وێنەیەک.",
            "سڵاو {name}! من یاریدەدەرێکی فرەزمانم. چیت پێویستە؟",
            "بەخێربێیت! هیچ پرسیارێک زۆر سەخت نییە.",
            "سڵاو! هەموو شتێک ئامادەیە — پرسیارەکەت بنووسە.",
            "بەخێربێی بۆ بنکەی BLACK HAT AI PRIME. من لێرەم.",
            "سڵاو {name}، چاوەڕێی پرسیارەکەتم.",
            "بەخێربێیت! پرسیار، کۆد، وێنە — هەموو شتێک.",
            "سڵاو! دەتوانم یارمەتیت بدەم لە نووسین و پرۆگرامسازی.",
            "بەخێربێی {name}! فەرموو چی دەوێت؟",
            "سڵاو، من لێرەم. یەکەم پرسیارت چییە؟",
            "بەخێربێی! ئامادەیم بۆ هەر پرسیارێک.",
            "سڵاو {name}! ئەمە بنکەی منە.",
            "بەخێربێیت! من AIـێکی تەواو ئامادەیم.",
            "سڵاو! چاوەڕوانی یەکەم پرسیارتم.",
            "بەخێربێی! هەر شتێک بە دڵتە، بنووسە.",
            "سڵاو، دەرفەتێکی نوێ — چ دەکەین؟",
            "بەخێربێیت بۆ مێزەکەم.",
            "سڵاو {name}! هیچ شتێک زۆر بچووک نییە.",
            "بەخێربێی — ئامرازەکانم ئامادەن.",
        ],
        "welcome_credit": [
            "💳 کرێدیتەکانت: <b>{credits}</b>\n📈 ڕۆژانە: <b>+1</b>\n🎁 نوێ: <b>5</b>",
            "کرێدیت: <b>{credits}</b> — ئامادەیت؟",
            "💳 {credits} کرێدیت ماوەتەوە.",
            "💳 کرێدیت: <b>{credits}</b>\n🎁 +5 بۆ نوێ · 📈 +1 ڕۆژانە",
            "کرێدیت: <b>{credits}</b>\n📈 +1 ڕۆژانە",
        ],
        "welcome_admin": [
            "👑 ئەدمین — /panel بۆ پانێل",
            "👑 بەخێربێی سەرۆک. /panel",
            "👑 ئەدمین دەستنیشانکرا. /panel ببینە.",
            "👑 تۆ بەڕێوەبەری ئەم بنکەیت. /panel",
            "👑 دەستپێگەیشتنی تەواو. /panel",
        ],
        "no_credits": [
            "⛔ <b>کرێدیتەکانت تەواو بوون</b>\n\n💳 کرێدیت: <b>{credits}</b>\n⏰ ڕۆژانە ١ کرێدیت زیاد دەکرێت\n📨 بۆ زیادکردن: @ALONE427 یان @malikdlashad3",
            "⛔ کرێدیت نەماوە.\n\n💳 کرێدیت: <b>{credits}</b>\n📨 @ALONE427 — @malikdlashad3",
            "⛔ تەواو — کرێدیت نەماوە.\n⏰ سبەینێ +1",
            "⛔ کرێدیت: <b>{credits}</b>\n📨 بۆ زیادکردن: @ALONE427",
            "⛔ کرێدیتەکانت تەواو بوون.\n📨 @ALONE427 — @malikdlashad3",
        ],
        "banned": [
            "🚫 تۆ لە بۆت باند کرابیت.",
            "🚫 دەستپێگەیشتن نییە — باندکراویت.",
            "🚫 باندکراویت. دواتر هەوڵ بدە.",
            "🚫 تۆ باندکراویت لەم بۆتە.",
            "🚫 باندکراو.",
        ],
        "panel_help": [
            "🎛 <b>پانێلی ئەدمین</b>\n\n📊 <code>/system</code> — ئامار\n👥 <code>/users</code> — بەکارهێنەران\n🚫 <code>/ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;</code>\n✅ <code>/unban &lt;id&gt;</code>\n💳 <code>/credit &lt;id&gt; &lt;n&gt;</code> — زیادکردن\n💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code> — کەمکردن\n📨 <code>/letter &lt;text&gt;</code> — بۆ هەمووان\n📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code> — بۆ یەک\n📜 <code>/history &lt;id&gt;</code> — داواکارییەکان",
            "🎛 پانێل:\n/system · /users · /ban · /unban · /credit · /credit2 · /letter · /letter2 · /history",
            "پانێلی ئەدمین — /system /users /ban /unban /credit /credit2 /letter /letter2 /history",
        ],
        "thinking": [
            "🧠 بیر دەکەمەوە...",
            "چاوەڕوان بە...",
            "یەک چرکە...",
            "💭 لە بیرکردندام...",
            "کەمێک ڕابوەستە...",
            "🧠 خەریکی وەڵامدانم...",
            "یەک چرکە — بیر.",
            "چاوەڕوان بە.",
            "🧠 لەسەر ئەم پرسیارەم...",
            "یەک چرکە...",
        ],
        "rate_limited": [
            "⏳ زۆر خێرایت — کەمێک بوەستە.",
            "⏳ سنووری خێرایی.",
            "هێواش بە — لێرەم.",
            "⏳ هێواشتر.",
            "سنوور گەیشت.",
            "⏳ کەمێک بوەستە.",
            "⏳ زۆر خێرایت.",
            "هێواش بە.",
            "⏳ سنوور.",
            "⏳ یەک چرکە.",
        ],
        "too_long": [
            "❌ نامەکەت زۆر درێژە — سنوور {limit} پیت.",
            "نامەکە لە {limit} پیت زیاترە.",
            "❌ زۆر درێژ ({limit}).",
            "نامەکەت لە {limit} پیت زیاترە.",
            "❌ زۆر درێژ — {limit}.",
            "نامەکە لە {limit} پیت زیاترە.",
            "❌ {limit} پیت سنوور.",
            "نامەکەت لە {limit} پیت زیاترە.",
            "❌ زۆر درێژ.",
            "نامەکە لە {limit} پیت زیاترە.",
        ],
        "error_api": [
            "❌ داواکاری سەرکەوتوو نەبوو.",
            "کێشەیەک لە OpenAI.",
            "وەڵام نەهات.",
            "❌ کێشەی API.",
            "پەیوەندی شکست.",
            "کێشەی quota یان API key.",
            "❌ پەیوەندی شکست.",
            "کێشەی پەیوەندی.",
            "وەڵام نەهات.",
            "❌ کێشەی API.",
        ],
        "id_info": [
            "🆔 ناسنامە: <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ناسنامە: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ناسنامە: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
        ],
        "lang_usage": [
            "🌐 /lang ku|en\n• ku — کوردی\n• en — English",
            "/lang ku — کوردی\n/lang en — English",
            "🌐 /lang ku|en",
        ],
        "lang_set": [
            "✅ زمان گۆڕدرا بۆ کوردی.",
            "🌐 ئێستا بە کوردی.",
            "✅ کوردی چالاک.",
        ],
        "vision_ack": [
            "🖼 وێنەکە شیدەکەم...",
            "چاوەڕوان بە...",
            "لەسەر وێنەکەم...",
        ],
        "vision_default": [
            "تکایە ئەم وێنەیە بە کوردی ڕوون بکەرەوە.",
            "ئەم وێنە چییە؟",
            "لەم وێنەیەدا چی دەبینیت؟",
        ],
        "unknown_cmd": [
            "فەرمانی نەناسراو. /help.",
            "ئەمە ناناسرێت. /help.",
            "ناناسرێت. /help.",
        ],
        "help_text": [
            "<b>📖 فەرمانەکان</b>\n\n/start — دەستپێکردن\n/help — یارمەتی\n/id — ناسنامە\n/lang ku — کوردی\n/lang en — ئینگلیزی\n\n<b>بەکارهێنان:</b>\nنامەیەک بنێرە — بۆتەکە وەڵامت دەداتەوە.\nهەر نامەیەک = ١ کرێدیت."
        ],
        "fallback": [
            "تێنەگەیشتم — بە شێوەیەکی تر بنووسە.",
            "زیاتر ڕوونی بکەرەوە.",
            "ببورە، تێنەگەیشتم.",
            "بە شێوەیەکی جیاواز هەوڵ بدە.",
            "نازانم — ڕوونی بکەرەوە.",
            "تێنەگەیشتم — دووبارە.",
            "زیاتر باس بکە.",
            "نازانم — زیاتر ڕوونی.",
            "ببورە، تێنەگەیشتم.",
            "هەوڵ بدە بە شێوەیەکی تر.",
        ],
    },
    "en": {
        "welcome": [
            "Hi {name}! Welcome to <b>BLACK HAT AI PRIME</b>.\n\n• Send a message to chat.\n• Send an image to analyze.\n• /lang ku|en to switch language.",
            "Welcome, {name}! Send a message or an image.",
            "Hello {name}! I'm a multilingual assistant.",
            "Welcome aboard! No question is too big.",
            "Hi! Type your question.",
            "Welcome to the bench. I'm here to help.",
            "Hey {name}, waiting on your question.",
            "Welcome! Questions, code, images — all welcome.",
            "Hi! I can help with writing, programming, analysis.",
            "Welcome, {name}! What's the order?",
            "Hi, I'm here. What's your first question?",
            "Welcome! Ready for any question.",
            "Hello {name}! This is my bench.",
            "Welcome aboard! Fully ready.",
            "Hi! Waiting on your message.",
            "Welcome! Type whatever's on your mind.",
            "Hi, fresh start.",
            "Welcome to the bench.",
            "Hi {name}! Nothing is too small.",
            "Welcome — all tools ready.",
        ],
        "welcome_credit": [
            "💳 Credits: <b>{credits}</b>\n📈 Daily: <b>+1</b>\n🎁 New: <b>5</b>",
            "Credits: <b>{credits}</b> — ready?",
            "💳 {credits} credits remaining.",
            "💳 Credits: <b>{credits}</b>\n🎁 +5 new · 📈 +1 daily",
            "Credits: <b>{credits}</b>\n📈 +1 daily",
        ],
        "welcome_admin": [
            "👑 Admin — /panel",
            "👑 Welcome, chief. /panel",
            "👑 Admin identified. See /panel.",
            "👑 You run this bench. /panel",
            "👑 Full access. /panel",
        ],
        "no_credits": [
            "⛔ <b>Out of credits</b>\n\n💳 Credits: <b>{credits}</b>\n⏰ +1 credit per day\n📨 To add: @ALONE427 or @malikdlashad3",
            "⛔ No credits.\n\n💳 Credits: <b>{credits}</b>\n📨 @ALONE427 — @malikdlashad3",
            "⛔ Done — no credits.\n⏰ +1 tomorrow",
            "⛔ Credits: <b>{credits}</b>\n📨 @ALONE427",
            "⛔ Out of credits.\n📨 @ALONE427 — @malikdlashad3",
        ],
        "banned": [
            "🚫 You are banned from this bot.",
            "🚫 Access denied — banned.",
            "🚫 Banned. Try later.",
            "🚫 You're banned.",
            "🚫 Banned.",
        ],
        "panel_help": [
            "🎛 <b>Admin panel</b>\n\n📊 <code>/system</code> — stats\n👥 <code>/users</code> — users\n🚫 <code>/ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;</code>\n✅ <code>/unban &lt;id&gt;</code>\n💳 <code>/credit &lt;id&gt; &lt;n&gt;</code>\n💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code>\n📨 <code>/letter &lt;text&gt;</code>\n📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code>\n📜 <code>/history &lt;id&gt;</code>",
            "🎛 Panel:\n/system · /users · /ban · /unban · /credit · /credit2 · /letter · /letter2 · /history",
            "Admin panel — /system /users /ban /unban /credit /credit2 /letter /letter2 /history",
        ],
        "thinking": [
            "🧠 Thinking...",
            "Hold on...",
            "One sec...",
            "💭 Processing...",
            "Bear with me...",
            "🧠 Working on it...",
            "One sec — thinking.",
            "Hold on.",
            "🧠 On this question...",
            "One sec...",
        ],
        "rate_limited": [
            "⏳ Too fast — pause.",
            "⏳ Rate limit.",
            "Slower — I'm here.",
            "⏳ Easy there.",
            "Limit reached.",
            "⏳ Pause a moment.",
            "⏳ Too fast.",
            "Slower.",
            "⏳ Limit.",
            "⏳ One sec.",
        ],
        "too_long": [
            "❌ Too long — limit {limit}.",
            "Exceeds {limit} chars.",
            "❌ Too long ({limit}).",
            "Exceeds {limit} chars.",
            "❌ Too long — {limit}.",
            "Exceeds {limit} chars.",
            "❌ {limit} limit.",
            "Exceeds {limit} chars.",
            "❌ Too long.",
            "Exceeds {limit} chars.",
        ],
        "error_api": [
            "❌ AI request failed.",
            "Something went wrong.",
            "No response.",
            "❌ API issue.",
            "Connection failed.",
            "Quota or API key issue.",
            "❌ Connection failed.",
            "Connection issue.",
            "No response.",
            "❌ API issue.",
        ],
        "id_info": [
            "🆔 Your ID: <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "Your ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "Your ID: <code>{user_id}</code>",
            "🆔 <code>{user_id}</code>",
            "ID: <code>{user_id}</code>",
        ],
        "lang_usage": [
            "🌐 /lang ku|en\n• ku — Kurdish\n• en — English",
            "/lang ku — Kurdish\n/lang en — English",
            "🌐 /lang ku|en",
        ],
        "lang_set": [
            "✅ Language switched to English.",
            "🌐 I'll speak English now.",
            "✅ English active.",
        ],
        "vision_ack": [
            "🖼 Reading image...",
            "Hold on...",
            "On the image...",
        ],
        "vision_default": [
            "Explain this image in Kurdish.",
            "What is this image?",
            "Describe everything you see.",
        ],
        "unknown_cmd": [
            "Unknown command. /help.",
            "Not recognized. /help.",
            "Unrecognized. /help.",
        ],
        "help_text": [
            "<b>📖 Commands</b>\n\n/start — start\n/help — help\n/id — your ID\n/lang ku — Kurdish\n/lang en — English\n\n<b>Usage:</b>\nSend a message — the bot replies.\nEach message = 1 credit."
        ],
        "fallback": [
            "I didn't catch that — rephrase?",
            "Add more detail.",
            "Sorry, I didn't understand.",
            "Try another way.",
            "Not sure — clarify?",
            "Didn't understand — try again.",
            "Tell me more.",
            "Don't know — clarify.",
            "Sorry, didn't catch that.",
            "Try a different way.",
        ],
    }
}

class SafeDict(dict):
    def __missing__(self, key): return ""

def get_text(lang, key, seed=None, **kwargs):
    lang = lang if lang in BANK else "ku"
    variants = BANK[lang].get(key, ["..."])
    if seed is not None:
        idx = sum(ord(c) for c in str(seed)) % len(variants)
    else:
        idx = 0
    template = variants[idx]
    try:
        return template.format_map(SafeDict(kwargs))
    except Exception:
        return template

# ==========================================
# 4. DATABASE SETUP
# ==========================================

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                lang TEXT DEFAULT 'ku',
                credits INTEGER DEFAULT 5,
                last_daily TEXT,
                banned_until TEXT,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

# ==========================================
# 5. USER & CREDIT HELPERS
# ==========================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def ensure_user(user):
    with db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, first_name, username, lang, credits, last_daily, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                last_seen = CURRENT_TIMESTAMP
        """, (user.id, user.first_name or "", user.username or "", DEFAULT_LANG, STARTING_CREDITS, datetime.utcnow().strftime("%Y-%m-%d")))

def apply_daily(user_id):
    today = datetime.utcnow().date()
    with db() as conn:
        row = conn.execute("SELECT last_daily FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row and row[0]:
            last = datetime.strptime(row[0], "%Y-%m-%d").date()
            days = (today - last).days
            if days > 0:
                days = min(days, DAILY_CAP_DAYS)
                conn.execute("""
                    UPDATE users SET credits = credits + ?, last_daily = ? WHERE user_id=?
                """, (days * DAILY_CREDITS, today.strftime("%Y-%m-%d"), user_id))

def get_credits(user_id):
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row else 0

def spend_credit(user_id):
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row[0] < 1:
            return False
        conn.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
        return True

def get_lang(user_id):
    with db() as conn:
        row = conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row and row[0] in ("ku", "en") else DEFAULT_LANG

def set_lang(user_id, lang):
    with db() as conn:
        conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))

def is_banned(user_id):
    with db() as conn:
        row = conn.execute("SELECT banned_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return False
        if row[0] == "forever":
            return True
        until = datetime.fromisoformat(row[0])
        if datetime.utcnow() > until:
            conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (user_id,))
            return False
        return True

def ban_user(user_id, duration):
    if duration == "forever":
        val = "forever"
    else:
        m = {"1h": 1/24, "1d": 1, "7d": 7, "30d": 30}
        if duration not in m: return False
        val = (datetime.utcnow() + timedelta(days=m[duration])).isoformat()
    with db() as conn:
        conn.execute("UPDATE users SET banned_until=? WHERE user_id=?", (val, user_id))
    return True

def save_message(user_id, role, content):
    with db() as conn:
        conn.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content[:4000]))
        conn.execute("""
            DELETE FROM chat_history WHERE user_id=? AND id NOT IN (
                SELECT id FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?
            )
        """, (user_id, user_id, MAX_HISTORY_ROWS))

def get_history(user_id):
    with db() as conn:
        rows = conn.execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, HISTORY_LIMIT)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def log_request(user_id, type_, content):
    with db() as conn:
        conn.execute("INSERT INTO requests (user_id, type, content) VALUES (?, ?, ?)", (user_id, type_, content[:500]))

# ==========================================
# 6. BOT HELPERS
# ==========================================

def safe_html(text):
    return html.escape(text or "", quote=False)

def split_msg(text, limit=3900):
    if len(text) <= limit: return [text]
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def send_msg(chat_id, text, lang, reply_to=None, reply_markup=None):
    full_text = text + get_footer(lang)
    for i, part in enumerate(split_msg(full_text)):
        bot.send_message(
            chat_id, part,
            reply_to_message_id=reply_to if i == 0 else None,
            reply_markup=reply_markup if i == 0 else None,
            disable_web_page_preview=True
        )

def rate_limited(user_id):
    now = time.time()
    with _recent_lock:
        bucket = _recent_requests.setdefault(user_id, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE: return True
        bucket.append(now)
    return False

def check_blocked(message):
    uid = message.from_user.id
    if is_admin(uid): return False
    if is_banned(uid):
        send_msg(message.chat.id, get_text(get_lang(uid), "banned"), get_lang(uid))
        return True
    return False

# ==========================================
# 7. HANDLERS - USER
# ==========================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if check_blocked(message): return
    ensure_user(message.from_user)
    apply_daily(message.from_user.id)
    lang = get_lang(message.from_user.id)
    credits = get_credits(message.from_user.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🆔 /id", "📖 /help")
    markup.row("🌐 /lang ku", "🌐 /lang en")

    name = safe_html(message.from_user.first_name or "دۆست")
    body = get_text(lang, "welcome", seed=message.from_user.id, name=name)
    body += "\n\n" + get_text(lang, "welcome_credit", seed=message.from_user.id, credits=credits)
    
    if is_admin(message.from_user.id):
        body += "\n\n" + get_text(lang, "welcome_admin", seed=message.from_user.id)

    send_msg(message.chat.id, body, lang, reply_markup=markup)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if check_blocked(message): return
    lang = get_lang(message.from_user.id)
    send_msg(message.chat.id, get_text(lang, "help_text"), lang)

@bot.message_handler(commands=["id"])
def cmd_id(message):
    if check_blocked(message): return
    lang = get_lang(message.from_user.id)
    send_msg(message.chat.id, get_text(lang, "id_info", user_id=message.from_user.id), lang)

@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    if check_blocked(message): return
    lang = get_lang(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return send_msg(message.chat.id, get_text(lang, "lang_usage"), lang)
    
    choice = parts[1].strip().lower()
    if choice in ("ku", "en"):
        set_lang(message.from_user.id, choice)
        send_msg(message.chat.id, get_text(choice, "lang_set"), choice)
    else:
        send_msg(message.chat.id, get_text(lang, "lang_usage"), lang)

# ==========================================
# 8. HANDLERS - ADMIN
# ==========================================

@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if not is_admin(message.from_user.id): return
    send_msg(message.chat.id, get_text(get_lang(message.from_user.id), "panel_help"), get_lang(message.from_user.id))

@bot.message_handler(commands=["system"])
def cmd_system(message):
    if not is_admin(message.from_user.id): return
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        banned = conn.execute("SELECT COUNT(*) FROM users WHERE banned_until IS NOT NULL").fetchone()[0]
        reqs = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        credits = conn.execute("SELECT SUM(credits) FROM users").fetchone()[0] or 0
    
    text = (
        "📊 <b>ئاماری سیستەم</b>\n\n"
        f"👥 بەکارهێنەران: <b>{total}</b>\n"
        f"🚫 باندکراو: <b>{banned}</b>\n"
        f"💬 داواکاری: <b>{reqs}</b>\n"
        f"💳 کرێدیتی ماوە: <b>{credits}</b>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["users"])
def cmd_users(message):
    if not is_admin(message.from_user.id): return
    with db() as conn:
        rows = conn.execute("SELECT user_id, username, first_name, credits FROM users ORDER BY last_seen DESC LIMIT 30").fetchall()
    
    lines = ["👥 <b>دوایین بەکارهێنەران</b>\n"]
    for r in rows:
        un = f"@{r[1]}" if r[1] else r[2]
        lines.append(f"<code>{r[0]}</code> · {safe_html(un)} · 💳{r[3]}")
    bot.send_message(message.chat.id, "\n".join(lines))

@bot.message_handler(commands=["ban", "unban", "credit", "credit2", "letter", "letter2", "history"])
def cmd_admin_actions(message):
    if not is_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    cmd = parts[0][1:]

    if cmd == "ban" and len(parts) == 3:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        if ban_user(uid, parts[2].lower()):
            bot.reply_to(message, f"🚫 باند کرا: <code>{uid}</code> ({parts[2]})")
        else:
            bot.reply_to(message, "ماوە نەناسراوە: forever|1h|1d|7d|30d")

    elif cmd == "unban" and len(parts) >= 2:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        with db() as conn: conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (uid,))
        bot.reply_to(message, f"✅ لابرا: <code>{uid}</code>")

    elif cmd in ("credit", "credit2") and len(parts) == 3:
        try:
            uid = int(parts[1])
            amt = int(parts[2])
        except: return bot.reply_to(message, "ID یان ژمارە هەڵەیە.")
        sign = 1 if cmd == "credit" else -1
        with db() as conn:
            row = conn.execute("SELECT credits FROM users WHERE user_id=?", (uid,)).fetchone()
            if row:
                new_val = max(0, row[0] + (sign * amt))
                conn.execute("UPDATE users SET credits=? WHERE user_id=?", (new_val, uid))
                bot.reply_to(message, f"💳 <code>{uid}</code> → <b>{new_val}</b>")
            else:
                bot.reply_to(message, "بەکارهێنەر نەدۆزرایەوە.")

    elif cmd == "letter" and len(parts) >= 2:
        text = parts[1] if len(parts) == 2 else parts[1] + " " + parts[2]
        with db() as conn: ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
        sent = 0
        for uid in ids:
            try:
                bot.send_message(uid, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(text)}")
                sent += 1
                time.sleep(0.05)
            except: pass
        bot.reply_to(message, f"✅ نێردرا: {sent}")

    elif cmd == "letter2" and len(parts) == 3:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        try:
            bot.send_message(uid, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(parts[2])}")
            bot.reply_to(message, "✅ نێردرا.")
        except: bot.reply_to(message, "❌ شکست.")

    elif cmd == "history" and len(parts) >= 2:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        with db() as conn:
            rows = conn.execute("SELECT type, content, created_at FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 15", (uid,)).fetchall()
        if not rows: return bot.reply_to(message, "هیچ داواکارییەک نییە.")
        text = f"📜 <b>داواکارییەکانی</b> <code>{uid}</code>\n\n"
        for r in rows: text += f"• [{r[0]}] {r[2]}\n  {safe_html((r[1] or '')[:100])}\n"
        bot.send_message(message.chat.id, text)

# ==========================================
# 9. HANDLERS - CHAT & VISION
# ==========================================

@bot.message_handler(content_types=["photo", "document"])
def handle_vision(message):
    if check_blocked(message): return
    uid = message.from_user.id
    ensure_user(message.from_user)
    lang = get_lang(uid)

    if not is_admin(uid):
        if rate_limited(uid): return send_msg(message.chat.id, get_text(lang, "rate_limited"), lang)
        if not spend_credit(uid):
            return send_msg(message.chat.id, get_text(lang, "no_credits", credits=get_credits(uid)), lang)

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    prompt = (message.caption or get_text(lang, "vision_default")).strip()
    status = bot.reply_to(message, get_text(lang, "vision_ack"))

    try:
        f = bot.get_file(file_id)
        raw = bot.download_file(f.file_path)
        encoded = base64.b64encode(raw).decode("ascii")

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                ]}
            ],
            max_tokens=MAX_OUTPUT_TOKENS
        )
        answer = resp.choices[0].message.content.strip() or "…"
        log_request(uid, "vision", prompt)
        
        bot.delete_message(message.chat.id, status.message_id)
        send_msg(message.chat.id, safe_html(answer), lang, reply_to=message.message_id)
    except Exception:
        log.exception("Vision failed")
        bot.edit_message_text(get_text(lang, "error_api"), message.chat.id, status.message_id)

@bot.message_handler(content_types=["text"], func=lambda m: not m.text.startswith("/"))
def handle_chat(message):
    if check_blocked(message): return
    uid = message.from_user.id
    ensure_user(message.from_user)
    lang = get_lang(uid)
    query = message.text.strip()

    if len(query) > MAX_INPUT_CHARS:
        return send_msg(message.chat.id, get_text(lang, "too_long", limit=MAX_INPUT_CHARS), lang)

    if not is_admin(uid):
        if rate_limited(uid): return send_msg(message.chat.id, get_text(lang, "rate_limited"), lang)
        if not spend_credit(uid):
            return send_msg(message.chat.id, get_text(lang, "no_credits", credits=get_credits(uid)), lang)

    status = bot.reply_to(message, get_text(lang, "thinking"))
    
    try:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(get_history(uid))
        msgs.append({"role": "user", "content": query})
        
        resp = client.chat.completions.create(
            model=OPENAI_MODEL, messages=msgs, temperature=0.7, max_tokens=MAX_OUTPUT_TOKENS
        )
        answer = resp.choices[0].message.content.strip() or "…"
        
        save_message(uid, "user", query)
        save_message(uid, "assistant", answer)
        log_request(uid, "chat", query)

        bot.delete_message(message.chat.id, status.message_id)
        send_msg(message.chat.id, safe_html(answer), lang, reply_to=message.message_id)
    except Exception:
        log.exception("Chat failed")
        bot.edit_message_text(get_text(lang, "error_api"), message.chat.id, status.message_id)

@bot.message_handler(content_types=["text"], func=lambda m: m.text.startswith("/"))
def handle_unknown(message):
    if is_admin(message.from_user.id) or check_blocked(message): return
    lang = get_lang(message.from_user.id)
    send_msg(message.chat.id, get_text(lang, "unknown_cmd"), lang)

# ==========================================
# 10. MAIN
# ==========================================

if __name__ == "__main__":
    init_db()
    log.info("Bot started. Admins: %s", ADMIN_IDS)
    try:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True, timeout=20)
    except Exception:
        log.exception("Polling crashed")
