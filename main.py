#!/usr/bin/env python3
"""BLACK HAT AI PRIME — full reply bank + credits + admin panel + footer."""

from __future__ import annotations

import base64
import hashlib
import html
import logging
import os
import re
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import telebot
from telebot import types
from openai import OpenAI

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", OPENAI_CHAT_MODEL).strip()
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ku").strip().lower()
if DEFAULT_LANG not in ("ku", "en"):
    DEFAULT_LANG = "ku"

ADMIN_IDS = {5527152252, 8487940066}

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
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("black-hat-prime")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0, max_retries=2)

_recent: dict[int, list[float]] = {}
_recent_lock = threading.Lock()

# ============================================================
# FOOTER
# ============================================================

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


def footer(lang: str) -> str:
    return FOOTER_KU if lang == "ku" else FOOTER_EN


# ============================================================
# BANK — full reply bank
# ============================================================

BANK: dict[str, dict[str, list[str]]] = {
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
        "greeting": [
            "سڵاو! چۆن یارمەتیت بدەم؟",
            "سڵاو — چیت پێویستە؟",
            "سڵاو، ئامادەیم.",
            "سڵاو! من لێرەم.",
            "سڵاو 👋 چ دەوێت؟",
            "سڵاو — دەست پێبکە.",
            "سڵاو! چ پرسیارێک هەیەت؟",
            "سڵاو، چۆنی؟",
            "سڵاو! ئامادەیم.",
            "سڵاو، چ هەواڵ؟",
        ],
        "farewell": [
            "بەخێر بێی! هەر کاتێک بگەڕێوە.",
            "خوا حافیز — بە سەلامەتی!",
            "بەخێر بێی. بەسوود بوو?",
            "دواتر بینین — سەرکەوتوو بیت.",
            "👋 بەخێر بێی!",
            "بەخێر بێی، من لێرەم.",
            "خوا حافیز! سەردانێکی باش.",
            "بەخێر بێی — دەرگا کراوەیە.",
            "دواتر بینین.",
            "👋 بەخێر بێی.",
        ],
        "thanks_reply": [
            "بەخێر بێی! من لێرەم.",
            "سوپاس بۆ تۆ — هیچ شتێکی تر؟",
            "خۆشحاڵم کە یارمەتیم دایت.",
            "🙏 بەخێر بێی.",
            "خوشحالم کە بەسوود بوو.",
            "بەخێر بێی! ئەمە کارەکەمە.",
            "سوپاس — هەموو شتێک باش بێت.",
            "بەخێر بێی، هیچ شتێک نییە.",
            "🙏 خۆشحاڵم.",
            "بەخێر بێی — ئەرکی منە.",
        ],
        "apology": [
            "ببورە — هەڵەیەکی من بوو.",
            "ببورە، بە دروستی ڕووی نەدا.",
            "ببورە بۆ تێنەگەیشتن.",
            "ببورە، باش نەبوو.",
            "ببورە، جارێکی تر هەوڵ دەدەم.",
            "ببورە، من هەڵە دەکەم.",
            "ببورە — ڕوونی بکەرەوە?",
            "ببورە، هەموو شتێک نازانم.",
            "ببورە، باشتر دەبم.",
            "ببورە — با دەست پێبکەین.",
        ],
        "acknowledge": [
            "باشە، تێدەگەم.",
            "تێدەگەم.",
            "ڕاستە، تێدەگەم.",
            "باشە، وەرگیرا.",
            "ئاها، تێدەگەم.",
            "باشە.",
            "تێدەگەم، بەردەوام بە.",
            "باشە — ڕوونە.",
            "وەرگیرا.",
            "تێدەگەم، سوپاس.",
        ],
        "agreement": [
            "بەڵێ، ڕاستە.",
            "بەڵێ، تەواو ڕاستە.",
            "بەڵێ، هەمان ڕایم هەیە.",
            "بەڵێ، ڕاستە.",
            "بەڵێ، تێدەگەم.",
            "بەڵێ، ڕاستە.",
            "بەڵێ، لەگەڵ تۆم.",
            "بەڵێ، هیچ گومانێک نییە.",
            "بەڵێ، وام دەبینم.",
            "بەڵێ، ڕاستە.",
        ],
        "disagreement": [
            "بەڵام، بە ڕێزەوە، جیاواز بیر دەکەمەوە.",
            "بەڵام شتێک لەبەرچاو نەگیراوە.",
            "بە ڕێزەوە، جیاواز دەبینم.",
            "بەڵام ڕێگایەکی تر هەیە.",
            "بەڵام لەوانەیە شتێک لەدەستمان بێت.",
            "بەڵام دەبێت زیاتر ڕوون بێت.",
            "بە ڕێزەوە، جیاواز.",
            "بەڵام ئەمە یەک ڕوانگەیە.",
            "بەڵام بە شێوەیەکی تر دەبینین.",
            "بە ڕێزەوە، جیاواز.",
        ],
        "compliment_reply": [
            "سوپاس! ئەمە کارەکەمە.",
            "سوپاس بۆ قسە شیرینەکانت.",
            "زۆر سوپاس — دڵخۆشم.",
            "🙏 سوپاس.",
            "سوپاس! هیوادارم باشتر بم.",
            "زۆر سوپاس.",
            "سوپاس! هەوڵ دەدەم.",
            "🙏 سوپاس.",
            "سوپاس بۆ متمانەت.",
            "زۆر سوپاس.",
        ],
        "encouragement": [
            "تۆ دەتوانیت! بەردەوام بە.",
            "هیوادارم سەرکەوتوو بیت.",
            "لەسەر ڕێگای ڕاستیت.",
            "با بەردەوام بین — نزیکە.",
            "باشتر دەبیت هەر ڕۆژێک.",
            "با دەست پێبکەین.",
            "هیچ شتێک زۆر سەخت نییە.",
            "بەردەوام بە.",
            "لەسەر ڕێگای دروستیت.",
            "هەنگاو بە هەنگاو.",
        ],
        "empathy": [
            "تێدەگەم کە سەختە.",
            "لەگەڵ تۆم.",
            "دەنگدانەوەی سروشتییە.",
            "تێدەگەم، ئاسان نییە.",
            "هیوادارم باشتر ببێت.",
            "تێدەگەم، قورسە.",
            "لێرەم بۆ تۆ.",
            "تێدەگەم، دۆخێکی سەختە.",
            "هیوادارم باش بێت.",
            "تێدەگەم، ناخۆشە.",
        ],
        "enthusiasm": [
            "ئەی! زۆر خۆشە!",
            "با دەست پێبکەین!",
            "ئەی، کارێکی خۆشە!",
            "زۆر خۆشە!",
            "ئەی! دڵخۆشکەرە!",
            "با بڕۆین!",
            "ئەی، پرسیارێکی باشە!",
            "زۆر خۆشە!",
            "ئەی! دەرفەتێکی باشە!",
            "هەنگاو بە هەنگاو!",
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
        "thinking_deep": [
            "🧠 پرسیارێکی قووڵ — کاتم پێویستە.",
            "💭 با بە وردی بیر بکەمەوە...",
            "ئاسان نییە — کەمێک کات.",
            "🧠 شیکردنەوەی قووڵ...",
            "با هەموو لایەنەکان ببینین...",
            "💭 بیرکردنەوەی ورد.",
            "پرسیارێکی سەخت.",
            "🧠 شیکردنەوەی زیاتر.",
            "با هێواشی بیر بکەمەوە...",
            "💭 شیکردنەوەی قووڵ.",
        ],
        "processing": [
            "⏳ لە پرۆسەدایە...",
            "خەریکی جێبەجێکردنم...",
            "یەک چرکە...",
            "⏳ خەریکی کارکردنم...",
            "یەک چرکە...",
            "لە پرۆسەدایە.",
            "⏳ جێبەجێکردن...",
            "یەک چرکە.",
            "خەریکی کارکردنم...",
            "⏳ لەسەرم...",
        ],
        "working_on_it": [
            "لەسەرم — کەمێک کات.",
            "خەریکی کارکردنم.",
            "لەسەر ئەمەم.",
            "خەریکم.",
            "لەسەرم.",
            "خەریکی کارکردنم.",
            "لەسەر پرسیارەکەم.",
            "خەریکم.",
            "لەسەرم، وەڵامێک دێت.",
            "خەریکی کارکردنم.",
        ],
        "verifying": [
            "لە پشکنینمدایە...",
            "خەریکی پشتڕاستکردنەوەم...",
            "با دڵنیا ببم...",
            "لە پشکنیندا.",
            "خەریکی پشتڕاستکردنەوەم.",
            "با پشکنین بکەم...",
            "لە پشکنینمدایە.",
            "خەریکی دڵنیابوونم...",
            "با دڵنیا ببم.",
            "لە پشکنیندا.",
        ],
        "chat_prompt_hint": [
            "باشە — نامەیەک بنووسە.",
            "فەرموو، چیت پێویستە؟",
            "ئامادەیم — پرسیارەکەت بنووسە.",
            "دەست پێبکە.",
            "باشە — دەست پێبکە.",
            "چیت پێویستە؟",
            "لێرەم — پرسیارەکەت.",
            "با دەست پێبکەین.",
            "هەر شتێک بە دڵتە.",
            "ئامادەیم.",
        ],
        "clarifying_question": [
            "دەتوانیت زیاتر ڕوونی بکەیتەوە؟",
            "کەمێک زیاتر باس بکە.",
            "نموونەیەک بدە؟",
            "بۆچی ئەمە دەتەوێت؟",
            "کەمێک ڕوونی بکەرەوە.",
            "باسی مەبەستەکەت بکە؟",
            "زانیاری زیاتر بدە.",
            "زیاتر ڕوونی بکەیتەوە؟",
            "نموونەیەک بدە.",
            "کەمێک زیاتر باس بکە.",
        ],
        "confirm_understanding": [
            "ئایا ڕاستە ئەگەر بڵێم...؟",
            "با دڵنیا ببم — مەبەستت ئەمەیە؟",
            "تێدەگەم ئەمە دەتەوێت؟",
            "با دڵنیا ببم — ڕاستە؟",
            "مەبەستت ئەمەیە؟",
            "با دڵنیا ببم...",
            "ئەمە ڕاستە؟",
            "با پشکنین بکەم — ئەمە مەبەستتە؟",
            "تێدەگەم؟",
            "با دڵنیا ببم — ڕاست تێدەگەم؟",
        ],
        "follow_up_offer": [
            "ئەگەر ویستت، زیاتر ڕوونی دەکەمەوە.",
            "ئەگەر پێویستت بوو، بڵێ.",
            "دەتوانم زیاتر باس بکەم.",
            "پێویستت بوو، لێرەم.",
            "زیاتر یارمەتیت دەدەم — بڵێ.",
            "نموونەیەک دەدەم ئەگەر ویستت.",
            "لێرەم.",
            "زیاتر ڕوونی دەکەمەوە.",
            "زیاتر یارمەتیت دەدەم.",
            "تەنها بڵێ.",
        ],
        "interesting_question": [
            "پرسیارێکی سەرنجڕاکێشە!",
            "پرسیارێکی باش.",
            "زۆر سەرنجڕاکێشە.",
            "پرسیارێکی باش.",
            "پرسیارێکی قووڵە.",
            "پرسیارێکی زۆر باش.",
            "سەرنجڕاکێشە.",
            "پرسیارێکی جوان.",
            "پرسیارێکی باش.",
            "سەرنجڕاکێش.",
        ],
        "good_question": [
            "پرسیارێکی باش!",
            "پرسیارێکی زۆر باش.",
            "باشە — پرسیارێکی گرنگ.",
            "پرسیارێکی باش.",
            "پرسیارێکی گرنگ.",
            "پرسیارێکی باش.",
            "پرسیارێکی زۆر باش.",
            "پرسیارێکی باش.",
            "پرسیارێکی باش.",
            "پرسیارێکی باش.",
        ],
        "hard_question": [
            "پرسیارێکی سەخت — ورد بین.",
            "پرسیارێکی قورس.",
            "ئاسان نییە — بیر بکەمەوە.",
            "پرسیارێکی سەخت.",
            "پرسیارێکی قورس.",
            "پرسیارێکی سەخت.",
            "ئاسان نییە.",
            "پرسیارێکی قورس.",
            "پرسیارێکی سەخت.",
            "پرسیارێکی سەخت.",
        ],
        "easy_question": [
            "ئاسانە — یەک چرکە.",
            "پرسیارێکی سادە.",
            "خێرا وەڵام.",
            "پرسیارێکی سادە.",
            "ئاسانە.",
            "پرسیارێکی سادە.",
            "ئاسانە.",
            "پرسیارێکی سادە.",
            "خێرا وەڵام.",
            "پرسیارێکی سادە.",
        ],
        "got_it": [
            "تێدەگەم.",
            "باشە، تێدەگەم.",
            "ڕاستە، تێدەگەم.",
            "باشە، وەرگیرا.",
            "ئاها، تێدەگەم.",
            "باشە، وەرگیرا.",
            "تێدەگەم، بەردەوام بە.",
            "باشە — ڕوونە.",
            "وەرگیرا، باشە.",
            "تێدەگەم، سوپاس.",
        ],
        "noted": [
            "تێبینی کرا.",
            "تۆمار کرا.",
            "وەرگیرا.",
            "تێبینی کرا.",
            "تۆمار کرا.",
            "وەرگیرا.",
            "تێبینی کرا.",
            "تۆمار کرا.",
            "وەرگیرا.",
            "تێبینی کرا.",
        ],
        "understood": [
            "تێدەگەم.",
            "باشە، تێدەگەم.",
            "ڕاستە.",
            "باشە، وەرگیرا.",
            "تێدەگەم، دەستخۆش.",
            "باشە، دەزانم.",
            "تێدەگەم.",
            "باشە، ڕوونە.",
            "وەرگیرا.",
            "تێدەگەم.",
        ],
        "next_step": [
            "هەنگاوی داهاتوو چییە؟",
            "با بڕۆینە هەنگاوی داهاتوو.",
            "دەست پێبکەین؟",
            "هەنگاو بە هەنگاو.",
            "هەنگاوی داهاتوو ئامادەیە.",
            "با دەست پێبکەین.",
            "بڕۆین بۆ هەنگاوی داهاتوو؟",
            "هەنگاوێک بەرەو پێش.",
            "داهاتوو — ئامادەیت؟",
            "با بەردەوام بین.",
        ],
        "quick_note": ["تێبینی:", "تێبینییەکی خێرا:", "تێبینییەکی بچووک:"],
        "additional_info": ["زانیاری زیاتر:", "زیاتر:", "زیاتر لەسەر ئەمە:"],
        "caveat_hint": ["تێبینییەکی گرنگ:", "بەڵام:", "سەرنج بدە:"],
        "break_down": ["با بەش بە بەش:", "با پارچە پارچە:", "هەنگاو بە هەنگاو:"],
        "explain_more": ["زیاتر ڕوونکردنەوە:", "زیاتر:", "بە وردی:"],
        "examples_ahead": ["نموونە:", "بۆ نموونە:", "نموونەیەک:"],
        "step_by_step": ["هەنگاو بە هەنگاو:", "هەنگاو ١، ٢، ٣...", "هەنگاوەکان:"],
        "short_answer": ["وەڵامی کورت:", "بە کورتی:", "کورت:"],
        "detailed_answer": ["وەڵامی ورد:", "بە وردی:", "وردەکاری:"],
        "positive_reinforce": ["باشە!", "زۆر باش!", "ئەی، باشە!"],
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
        "no_answer": [
            "وەڵامێک نەگەڕایەوە.",
            "هیچ وەڵامێک.",
            "وەڵام بەتاڵ.",
            "وەڵامێک نەهات.",
            "وەڵام بەتاڵ.",
            "هیچ وەڵامێک.",
            "وەڵامێک نەهات.",
            "وەڵام بەتاڵ.",
            "وەڵامێک نەگەڕایەوە.",
            "هیچ وەڵامێک.",
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
        "error_vision": [
            "❌ کێشەی وێنە. API بپشکنە.",
            "شیکردنەوەی وێنە سەرکەوتوو نەبوو.",
            "کێشەی vision.",
            "❌ کێشەی وێنە.",
            "شیکردنەوە شکست.",
            "کێشەی vision.",
            "❌ بینینی وێنە شکست.",
            "کێشە لە وێنە.",
            "❌ vision شکست.",
            "شیکردنەوە شکست.",
        ],
        "image_too_big": [
            "❌ وێنەکە زۆر گەورەیە — {mb}MB.",
            "لە {mb}MB زیاترە.",
            "❌ زۆر گەورە — {mb}MB.",
            "لە {mb}MB زیاترە.",
            "❌ {mb}MB سنوور.",
            "لە {mb}MB زیاترە.",
            "❌ زۆر گەورە.",
            "لە {mb}MB زیاترە.",
            "❌ {mb}MB.",
            "لە {mb}MB زیاترە.",
        ],
        "unexpected_error": [
            "⚠️ هەڵەی نەخوازراو.",
            "کێشەیەک ڕوویدا.",
            "⚠️ شتێک ڕاست نەبوو.",
            "⚠️ هەڵە.",
            "کێشە ڕوویدا.",
            "⚠️ شتێک ڕاست نەبوو.",
            "هەڵە ڕوویدا.",
            "⚠️ کێشە.",
            "⚠️ هەڵە.",
            "کێشە ڕوویدا.",
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
        "no_history": [
            "هیچ مێژووێک نییە.",
            "مێژوو بەتاڵە.",
            "هیچ تۆمارێک.",
            "مێژوو بەتاڵ.",
            "هیچ مێژوو.",
            "مێژوو بەتاڵ.",
            "هیچ تۆمار.",
            "مێژوو بەتاڵ.",
            "هیچ مێژوو.",
            "مێژوو بەتاڵ.",
        ],
        "cleared": [
            "✅ مێژوو سڕایەوە ({count}).",
            "🧹 پاککرایەوە ({count}).",
            "مێژوو سڕایەوە.",
            "✅ {count} تۆمار سڕایەوە.",
            "🧹 {count} سڕایەوە.",
            "✅ مێژوو سڕایەوە.",
            "🧹 پاککرایەوە.",
            "✅ {count} تۆمار.",
            "🧹 پاک.",
            "✅ مێژوو سڕایەوە.",
        ],
        "not_admin": [
            "تەنها ئەدمین.",
            "🚫 دەستپێگەیشتن نییە.",
            "بۆ ئەدمین.",
            "🚫 ئەدمین تەنها.",
            "تەنها ئەدمین.",
            "🚫 نییە.",
            "بۆ ئەدمین.",
            "🚫 ئەدمین.",
            "تەنها ئەدمین.",
            "🚫 نییە.",
        ],
        "lang_usage": [
            "🌐 /lang ku|en\n• ku — کوردی\n• en — English",
            "/lang ku — کوردی\n/lang en — English",
            "🌐 /lang ku|en",
        ],
        "lang_invalid": ["زمانی نەناسراو. ku یان en.", "تەنها ku یان en.", "ku یان en."],
        "lang_switched": [
            "✅ زمان گۆڕدرا بۆ کوردی.",
            "🌐 ئێستا بە کوردی.",
            "✅ کوردی چالاک.",
        ],
        "lang_switched_en": [
            "✅ Language switched to English.",
            "🌐 I'll speak English now.",
            "✅ English active.",
        ],
        "unknown_command": [
            "فەرمانی نەناسراو. /help.",
            "ئەمە ناناسرێت. /help.",
            "ناناسرێت. /help.",
        ],
        "cancel": ["هەڵوەشێنرا.", "باشە، هەڵوەشێنرا.", "وەستا."],
        "wait": ["کەمێک چاوەڕوان بە...", "یەک چرکە...", "لەسەرم..."],
        "confirmed": ["✅ پشتڕاستکرایەوە.", "تەواو — جێبەجێ کرا.", "باشە."],
        "denied": ["نەخێر.", "نەکرا.", "ڕەتکرایەوە."],
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
        "vision_ack": ["🖼 وێنەکە شیدەکەم...", "چاوەڕوان بە...", "لەسەر وێنەکەم..."],
        "vision_default_prompt": [
            "تکایە ئەم وێنەیە بە کوردی ڕوون بکەرەوە.",
            "ئەم وێنە چییە؟",
            "لەم وێنەیەدا چی دەبینیت؟",
        ],
        "label_user": ["تۆ"],
        "label_ai": ["AI"],
        "setup_menu": [
            "🚀 دامەزراندن — یەکێک هەڵبژێرە:\n/setup — ڕێنمایی تەواو\n/tool python — پایتۆن\n/tool pip — pip\n/tool git — git\n/tool nano — nano\n/tool tmux — tmux\n/tool env — .env\n/tool token — تۆکنی تێلیگرام\n/tool openai — OpenAI key\n/tool admin — ئەدمین\n/tool run — ڕەنکردن\n/tool errors — کێشەکان",
        ],
        "admin_help": [
            "🎛 <b>پانێلی ئەدمین</b>\n\n📊 <code>/system</code> — ئامار\n👥 <code>/users</code> — بەکارهێنەران\n🚫 <code>/ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;</code>\n✅ <code>/unban &lt;id&gt;</code>\n💳 <code>/credit &lt;id&gt; &lt;n&gt;</code>\n💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code>\n📨 <code>/letter &lt;text&gt;</code>\n📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code>\n📜 <code>/history &lt;id&gt;</code>",
        ],
        "model_info": [
            "چات: {chat_model}\nڤیژن: {vision_model}",
            "مۆدێل: {chat_model} / {vision_model}",
            "🤖 {chat_model} · 🖼 {vision_model}",
        ],
        "model_usage": [
            "شێواز: /model <chat|vision> <name>",
            "نموونە: /model chat gpt-4o-mini",
        ],
        "model_bad_kind": ["تەنها chat یان vision.", "chat یان vision.", "جۆر نەناسراو."],
        "model_set": ["✅ {kind} → {name}", "{kind}: {name}", "✅ {kind}: {name}"],
        "broadcast_usage": ["شێواز: /letter <text>", "نموونە: /letter سڵاو!"],
        "broadcast_progress": [
            "📤 {done}/{total} — نێردرا: {sent} · شکستی: {failed}",
            "لە بەردەستدایە... {done}/{total}",
        ],
        "broadcast_done": [
            "✅ نێردرا: {sent} · شکستی: {failed}",
            "تەواو — {sent} نێردرا، {failed} شکست.",
        ],
        "stats_info": [
            "👥 بەکارهێنەران: {users}\n🟢 چالاک: {active}\n💬 نامەکان: {messages}",
            "📊 {users} · 🟢 {active} · 💬 {messages}",
        ],
        "export_empty": ["هیچ بەکارهێنەرێک نییە.", "بنکە بەتاڵە."],
        "export_caption": ["{count} بەکارهێنەر", "📄 {count} بەکارهێنەر"],
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
        "greeting": [
            "Hey! How can I help?",
            "Hi — what do you need?",
            "Hello, ready.",
            "Hi! I'm here.",
            "Hey 👋 what's up?",
            "Hi — start whenever.",
            "Hey! What's your question?",
            "Hey, how are you?",
            "Hi! Ready — go ahead.",
            "Hey, what do you need?",
        ],
        "farewell": [
            "Goodbye! Come back whenever.",
            "Take care — safe travels!",
            "See you. Hope useful.",
            "Later — all the best.",
            "👋 Bye!",
            "Goodbye, I'm here.",
            "Take care!",
            "Bye — door open.",
            "See you.",
            "👋 Bye.",
        ],
        "thanks_reply": [
            "You're welcome! I'm here.",
            "Thanks to you — anything else?",
            "Glad I could help.",
            "🙏 You're welcome.",
            "Happy it was useful.",
            "You're welcome! That's my job.",
            "Thanks — hope all well.",
            "You're welcome, no problem.",
            "🙏 Glad I helped.",
            "You're welcome — my task.",
        ],
        "apology": [
            "Sorry — that was my mistake.",
            "Sorry, that didn't work.",
            "Sorry for the misunderstanding.",
            "Sorry, that wasn't good.",
            "Sorry, I'll try again.",
            "Sorry, I make mistakes.",
            "Sorry — can you clarify?",
            "Sorry, I don't know everything.",
            "Sorry, I'll do better.",
            "Sorry — let's restart.",
        ],
        "acknowledge": [
            "Okay, understood.",
            "Got it.",
            "Right, understood.",
            "Okay, received.",
            "Aha, understood.",
            "Okay.",
            "Understood, go on.",
            "Okay — clear.",
            "Received.",
            "Understood, thanks.",
        ],
        "agreement": [
            "Yes, right.",
            "Yes, completely.",
            "Yes, same view.",
            "Yes, right.",
            "Yes, understood.",
            "Yes, right.",
            "Yes, with you.",
            "Yes, no doubt.",
            "Yes, same way.",
            "Yes, right.",
        ],
        "disagreement": [
            "But respectfully, I think differently.",
            "But something is overlooked.",
            "Respectfully, I see it differently.",
            "But there's another way.",
            "But maybe we're missing something.",
            "But it should be clearer.",
            "Respectfully, differently.",
            "But that's one perspective.",
            "But we can see it another way.",
            "Respectfully, differently.",
        ],
        "compliment_reply": [
            "Thanks! That's my job.",
            "Thanks for the kind words.",
            "Thank you — happy.",
            "🙏 Thanks.",
            "Thanks! Hope I stay good.",
            "Thank you.",
            "Thanks! I try.",
            "🙏 Thanks.",
            "Thanks for trusting me.",
            "Thank you.",
        ],
        "encouragement": [
            "You can do it! Keep going.",
            "Hope you succeed.",
            "On the right path.",
            "Let's keep going.",
            "Better every day.",
            "Let's start.",
            "Nothing too hard.",
            "Keep going.",
            "Right path.",
            "Step by step.",
        ],
        "empathy": [
            "I understand this is hard.",
            "I'm with you.",
            "Natural reaction.",
            "I understand, isn't easy.",
            "Hope better.",
            "I understand, tough.",
            "Here for you.",
            "I understand, difficult.",
            "Hope all okay.",
            "I understand, unpleasant.",
        ],
        "enthusiasm": [
            "Oh! Great!",
            "Let's start!",
            "Oh, nice job!",
            "Very nice!",
            "Oh! Exciting!",
            "Let's go!",
            "Oh, good question!",
            "Very nice!",
            "Oh! Good opportunity!",
            "Step by step!",
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
        "thinking_deep": [
            "🧠 Deep question — need time.",
            "💭 Let me think carefully...",
            "Not easy — a moment.",
            "🧠 Deep analysis...",
            "Let me see all angles...",
            "💭 Careful thinking.",
            "Hard question.",
            "🧠 More analysis.",
            "Let me think slowly...",
            "💭 Deep analysis.",
        ],
        "processing": [
            "⏳ Processing...",
            "Working on it...",
            "One sec...",
            "⏳ Working...",
            "One sec...",
            "Processing.",
            "⏳ Executing...",
            "One sec.",
            "Working...",
            "⏳ On it...",
        ],
        "working_on_it": [
            "On it — one moment.",
            "Working on this.",
            "On this.",
            "Working.",
            "On it.",
            "Working on this.",
            "On this question.",
            "Working.",
            "On it, answer coming.",
            "Working.",
        ],
        "verifying": [
            "Verifying...",
            "Double-checking...",
            "Let me be sure...",
            "Checking.",
            "Double-checking.",
            "Let me check...",
            "Verifying.",
            "Making sure...",
            "Let me be sure.",
            "Checking.",
        ],
        "chat_prompt_hint": [
            "Alright — send a message.",
            "Go ahead, what do you need?",
            "Ready — type your question.",
            "Start whenever.",
            "Alright — start.",
            "What do you need?",
            "Here — type your question.",
            "Okay, let's start.",
            "Type whatever's on your mind.",
            "Ready.",
        ],
        "clarifying_question": [
            "Can you clarify a bit more?",
            "Tell me a bit more.",
            "Can you give an example?",
            "Why do you want this?",
            "Please clarify.",
            "Can you describe your intent?",
            "Give more info.",
            "Can you clarify more?",
            "An example would help.",
            "Tell me more.",
        ],
        "confirm_understanding": [
            "Is it right if I say...?",
            "Let me be sure — is this your intent?",
            "Do I understand?",
            "Let me be sure — right?",
            "Is this your intent?",
            "Let me make sure...",
            "Is this right?",
            "Let me check.",
            "Do I understand?",
            "Let me be sure.",
        ],
        "follow_up_offer": [
            "If you'd like, I can explain more.",
            "If needed, just say.",
            "I can go deeper.",
            "If you need, I'm here.",
            "I can help more — just say.",
            "If you want, an example.",
            "I'm here.",
            "I can clarify more.",
            "I can help more.",
            "Just say.",
        ],
        "interesting_question": [
            "Interesting question!",
            "Good question.",
            "Very interesting.",
            "Good question.",
            "Deep question.",
            "Very good question.",
            "Interesting.",
            "Nice question.",
            "Good question.",
            "Interesting.",
        ],
        "good_question": [
            "Good question!",
            "Very good question.",
            "Good — important.",
            "Good question.",
            "Important question.",
            "Good question.",
            "Very good.",
            "Good question.",
            "Good question.",
            "Good question.",
        ],
        "hard_question": [
            "Hard question — careful.",
            "Tough question.",
            "Not easy — think carefully.",
            "Hard question.",
            "Tough question.",
            "Hard question.",
            "Not easy.",
            "Tough question.",
            "Hard question.",
            "Hard question.",
        ],
        "easy_question": [
            "Easy — one sec.",
            "Simple question.",
            "Quick to answer.",
            "Simple question.",
            "Easy.",
            "Simple question.",
            "Easy.",
            "Simple question.",
            "Quick.",
            "Simple question.",
        ],
        "got_it": [
            "Got it.",
            "Okay, understood.",
            "Right, understood.",
            "Okay, received.",
            "Aha, understood.",
            "Okay, got it.",
            "Understood, go on.",
            "Okay — clear.",
            "Received, okay.",
            "Understood, thanks.",
        ],
        "noted": [
            "Noted.",
            "Recorded.",
            "Received.",
            "Noted.",
            "Recorded.",
            "Received.",
            "Noted.",
            "Recorded.",
            "Received.",
            "Noted.",
        ],
        "understood": [
            "Understood.",
            "Okay, understood.",
            "Right.",
            "Okay, received.",
            "Understood, thanks.",
            "Okay, I know.",
            "Understood.",
            "Okay, clear.",
            "Received.",
            "Understood.",
        ],
        "next_step": [
            "What's the next step?",
            "Let's move.",
            "Can we start?",
            "Step by step.",
            "Next step ready.",
            "Let's start.",
            "Next step?",
            "One step forward.",
            "Next — ready?",
            "Let's keep going.",
        ],
        "quick_note": ["Note:", "Quick note:", "A small note:"],
        "additional_info": ["More info:", "More:", "More on this:"],
        "caveat_hint": ["Important note:", "But:", "Pay attention:"],
        "break_down": ["Let's break down:", "Step by step:", "Parts:"],
        "explain_more": ["More explanation:", "More:", "In detail:"],
        "examples_ahead": ["Example:", "For example:", "An example:"],
        "step_by_step": ["Step by step:", "Step 1, 2, 3...", "Steps:"],
        "short_answer": ["Short answer:", "In short:", "Brief:"],
        "detailed_answer": ["Detailed answer:", "In detail:", "Details:"],
        "positive_reinforce": ["Good!", "Very good!", "Oh, good!"],
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
        "no_answer": [
            "No response came back.",
            "No answer.",
            "Empty response.",
            "No response.",
            "Empty.",
            "No answer.",
            "No response.",
            "Empty.",
            "No response.",
            "No answer.",
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
        "error_vision": [
            "❌ Image issue. Check API.",
            "Image analysis failed.",
            "Vision issue.",
            "❌ Image issue.",
            "Analysis failed.",
            "Vision issue.",
            "❌ Vision failed.",
            "Image issue.",
            "❌ Vision failed.",
            "Analysis failed.",
        ],
        "image_too_big": [
            "❌ Image too large — {mb}MB.",
            "Exceeds {mb}MB.",
            "❌ Too large — {mb}MB.",
            "Exceeds {mb}MB.",
            "❌ {mb}MB limit.",
            "Exceeds {mb}MB.",
            "❌ Too large.",
            "Exceeds {mb}MB.",
            "❌ {mb}MB.",
            "Exceeds {mb}MB.",
        ],
        "unexpected_error": [
            "⚠️ Unexpected error.",
            "Something went wrong.",
            "⚠️ Something off.",
            "⚠️ Error.",
            "Something wrong.",
            "⚠️ Something off.",
            "Error occurred.",
            "⚠️ Issue.",
            "⚠️ Error.",
            "Something wrong.",
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
        "no_history": [
            "No history yet.",
            "History is empty.",
            "No records.",
            "History empty.",
            "No history.",
            "History empty.",
            "No records.",
            "History empty.",
            "No history.",
            "History empty.",
        ],
        "cleared": [
            "✅ History cleared ({count}).",
            "🧹 Cleared ({count}).",
            "History cleared.",
            "✅ {count} entries cleared.",
            "🧹 {count} cleared.",
            "✅ History cleared.",
            "🧹 Cleared.",
            "✅ {count} entries.",
            "🧹 Cleared.",
            "✅ History cleared.",
        ],
        "not_admin": [
            "Admin-only.",
            "🚫 Access denied.",
            "Admins only.",
            "🚫 Admin only.",
            "Only admins.",
            "🚫 Denied.",
            "Admins only.",
            "🚫 Admin.",
            "Only admins.",
            "🚫 Denied.",
        ],
        "lang_usage": [
            "🌐 /lang ku|en\n• ku — Kurdish\n• en — English",
            "/lang ku — Kurdish\n/lang en — English",
            "🌐 /lang ku|en",
        ],
        "lang_invalid": ["Unknown language. ku or en.", "Only ku or en.", "ku or en."],
        "lang_switched": [
            "✅ Language switched to English.",
            "🌐 I'll speak English now.",
            "✅ English active.",
        ],
        "lang_switched_en": [
            "✅ Language switched to English.",
            "🌐 I'll speak English now.",
            "✅ English active.",
        ],
        "unknown_command": [
            "Unknown command. /help.",
            "Not recognized. /help.",
            "Unrecognized. /help.",
        ],
        "cancel": ["Cancelled.", "Okay, cancelled.", "Stopped."],
        "wait": ["Hold on...", "One sec...", "On it..."],
        "confirmed": ["✅ Confirmed.", "Done — executed.", "Alright."],
        "denied": ["No.", "Not done.", "Denied."],
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
        "vision_ack": ["🖼 Reading image...", "Hold on...", "On the image..."],
        "vision_default_prompt": [
            "Explain this image in Kurdish.",
            "What is this image?",
            "Describe everything you see.",
        ],
        "label_user": ["You"],
        "label_ai": ["AI"],
        "setup_menu": [
            "🚀 Setup — pick one:\n/setup — full guide\n/tool python\n/tool pip\n/tool git\n/tool nano\n/tool tmux\n/tool env\n/tool token\n/tool openai\n/tool admin\n/tool run\n/tool errors",
        ],
        "admin_help": [
            "🎛 <b>Admin panel</b>\n\n📊 <code>/system</code>\n👥 <code>/users</code>\n🚫 <code>/ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;</code>\n✅ <code>/unban &lt;id&gt;</code>\n💳 <code>/credit &lt;id&gt; &lt;n&gt;</code>\n💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code>\n📨 <code>/letter &lt;text&gt;</code>\n📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code>\n📜 <code>/history &lt;id&gt;</code>",
        ],
        "model_info": [
            "Chat: {chat_model}\nVision: {vision_model}",
            "Model: {chat_model} / {vision_model}",
            "🤖 {chat_model} · 🖼 {vision_model}",
        ],
        "model_usage": [
            "Usage: /model <chat|vision> <name>",
            "Example: /model chat gpt-4o-mini",
        ],
        "model_bad_kind": ["Only chat or vision.", "chat or vision.", "Unknown kind."],
        "model_set": ["✅ {kind} → {name}", "{kind}: {name}", "✅ {kind}: {name}"],
        "broadcast_usage": ["Usage: /letter <text>", "Example: /letter Hello!"],
        "broadcast_progress": [
            "📤 {done}/{total} — sent: {sent} · failed: {failed}",
            "Working... {done}/{total}",
        ],
        "broadcast_done": [
            "✅ Sent: {sent} · Failed: {failed}",
            "Done — {sent} delivered, {failed} failed.",
        ],
        "stats_info": [
            "👥 Users: {users}\n🟢 Active: {active}\n💬 Messages: {messages}",
            "📊 {users} · 🟢 {active} · 💬 {messages}",
        ],
        "export_empty": ["No users yet.", "Database empty."],
        "export_caption": ["{count} users", "📄 {count} users"],
    },
}


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def pick(lang: str, category: str, seed=None, **kwargs) -> str:
    bank = BANK.get(lang) or BANK[DEFAULT_LANG]
    variants = bank.get(category)
    if not variants:
        variants = bank.get("fallback", ["…"])
    if seed is None:
        seed = 0
    key = f"{lang}:{category}:{seed}".encode("utf-8")
    idx = int.from_bytes(hashlib.sha256(key).digest()[:4], "big")
    template = variants[idx % len(variants)]
    try:
        return template.format_map(_SafeDict(kwargs))
    except (KeyError, IndexError, ValueError, AttributeError):
        return template


# ============================================================
# DATABASE
# ============================================================

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
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
                total_requests INTEGER DEFAULT 0,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_history_user
                ON chat_history(user_id, id DESC);
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_requests_user
                ON requests(user_id, id DESC);
        """)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for col, defn in [
            ("credits", "INTEGER DEFAULT 5"),
            ("last_daily", "TEXT"),
            ("banned_until", "TEXT"),
            ("total_requests", "INTEGER DEFAULT 0"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")


def today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def ensure_user(user) -> None:
    with db() as conn:
        row = conn.execute(
            "SELECT user_id FROM users WHERE user_id=?", (user.id,)
        ).fetchone()
        if row is None:
            conn.execute(
                """INSERT INTO users(user_id, first_name, username, lang,
                        credits, last_daily, last_seen)
                   VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (user.id, user.first_name or "", user.username or "",
                 DEFAULT_LANG, STARTING_CREDITS, today_str()),
            )
        else:
            conn.execute(
                """UPDATE users SET first_name=?, username=?,
                        last_seen=CURRENT_TIMESTAMP
                   WHERE user_id=?""",
                (user.first_name or "", user.username or "", user.id),
            )


def apply_daily(user_id: int) -> None:
    today = datetime.utcnow().date()
    with db() as conn:
        row = conn.execute(
            "SELECT last_daily FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row or not row[0]:
            return
        try:
            last = datetime.strptime(row[0], "%Y-%m-%d").date()
        except ValueError:
            return
        days = (today - last).days
        if days <= 0:
            return
        days = min(days, DAILY_CAP_DAYS)
        conn.execute(
            "UPDATE users SET credits = credits + ?, last_daily = ? "
            "WHERE user_id=?",
            (days * DAILY_CREDITS, today.strftime("%Y-%m-%d"), user_id),
        )


def get_credits(user_id: int) -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT credits FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def spend_credit(user_id: int, amount: int = 1) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT credits FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row or row[0] < amount:
            return False
        conn.execute(
            "UPDATE users SET credits = credits - ? WHERE user_id=?",
            (amount, user_id),
        )
        conn.execute(
            "UPDATE users SET total_requests = total_requests + 1 "
            "WHERE user_id=?", (user_id,),
        )
    return True


def get_lang(user_id: int) -> str:
    with db() as conn:
        row = conn.execute(
            "SELECT lang FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return (row[0] if row and row[0] else DEFAULT_LANG) or DEFAULT_LANG


def set_lang(user_id: int, lang: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE users SET lang=? WHERE user_id=?", (lang, user_id)
        )


def is_banned(user_id: int) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT banned_until FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row or not row[0]:
            return False
        if row[0] == "forever":
            return True
        try:
            until = datetime.fromisoformat(row[0])
        except ValueError:
            return True
        if datetime.utcnow() > until:
            conn.execute(
                "UPDATE users SET banned_until=NULL WHERE user_id=?",
                (user_id,),
            )
            return False
        return True


def ban_user(user_id: int, duration: str) -> bool:
    if duration == "forever":
        banned_until = "forever"
    else:
        m = {"1h": timedelta(hours=1), "1d": timedelta(days=1),
             "7d": timedelta(days=7), "30d": timedelta(days=30)}
        delta = m.get(duration)
        if not delta:
            return False
        banned_until = (datetime.utcnow() + delta).isoformat()
    with db() as conn:
        conn.execute(
            "UPDATE users SET banned_until=? WHERE user_id=?",
            (banned_until, user_id),
        )
        if conn.total_changes == 0:
            conn.execute(
                "INSERT OR IGNORE INTO users(user_id, banned_until) "
                "VALUES(?,?)", (user_id, banned_until),
            )
    return True


def unban_user(user_id: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE users SET banned_until=NULL WHERE user_id=?",
            (user_id,),
        )


def save_message(user_id: int, role: str, content: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)",
            (user_id, role, content[:12000]),
        )
        conn.execute(
            """DELETE FROM chat_history WHERE user_id=? AND id NOT IN (
                SELECT id FROM chat_history WHERE user_id=?
                ORDER BY id DESC LIMIT ?)""",
            (user_id, user_id, MAX_HISTORY_ROWS),
        )


def get_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_history "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    rows.reverse()
    return [{"role": r, "content": c} for r, c in rows]


def log_request(user_id: int, type_: str, content: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO requests(user_id, type, content) VALUES(?,?,?)",
            (user_id, type_, content[:2000]),
        )


def get_requests(user_id: int, limit: int = 20) -> list[tuple]:
    with db() as conn:
        return conn.execute(
            "SELECT type, content, created_at FROM requests "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


# ============================================================
# SEND
# ============================================================

def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def split_safe(text: str, limit: int = 3900) -> list[str]:
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]
    parts = []
    buf = ""
    for word in text.split(" "):
        if len(buf) + len(word) + 1 > limit:
            if buf:
                parts.append(buf)
            buf = word
        else:
            buf = (buf + " " + word) if buf else word
        while len(buf) > limit:
            cut = limit
            tail = buf[:cut]
            amp = tail.rfind("&")
            semi = tail.rfind(";")
            if amp != -1 and (semi == -1 or semi < amp) and cut - amp <= 12:
                cut = amp
            if cut <= 0:
                cut = 1
            parts.append(buf[:cut])
            buf = buf[cut:]
    if buf:
        parts.append(buf)
    return parts or [""]


def send(chat_id: int, html_body: str, lang: str,
         reply_to: int | None = None,
         reply_markup=None) -> None:
    full = html_body + footer(lang)
    for i, part in enumerate(split_safe(full)):
        if not part:
            continue
        try:
            bot.send_message(
                chat_id, part,
                reply_to_message_id=reply_to if i == 0 else None,
                reply_markup=reply_markup if i == 0 else None,
                disable_web_page_preview=True,
            )
        except Exception:
            log.exception("send failed")


def typing(chat_id: int) -> None:
    try:
        bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass


def typing_loop(chat_id: int, stop: threading.Event) -> None:
    while not stop.is_set():
        typing(chat_id)
        stop.wait(4.0)


def rate_limited(user_id: int) -> bool:
    now = time.time()
    with _recent_lock:
        if len(_recent) > 10_000:
            _recent.clear()
        bucket = _recent.setdefault(user_id, [])
        bucket[:] = [t for t in bucket if now - t < 60.0]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            return True
        bucket.append(now)
    return False


def call_ai(messages: list[dict]) -> str:
    resp = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip() or "…"


def check_blocked(message) -> bool:
    user_id = message.from_user.id
    if is_admin(user_id):
        return False
    if is_banned(user_id):
        lang = get_lang(user_id)
        send(message.chat.id, pick(lang, "banned", seed=user_id), lang)
        return True
    return False


# ============================================================
# USER HANDLERS
# ============================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if check_blocked(message):
        return
    ensure_user(message.from_user)
    apply_daily(message.from_user.id)
    lang = get_lang(message.from_user.id)
    credits = get_credits(message.from_user.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🆔 /id", "📖 /help")
    markup.row("🌐 /lang ku", "🌐 /lang en")

    name = esc(message.from_user.first_name or "دۆست")
    body = pick(lang, "welcome", seed=message.from_user.id, name=name)
    body += "\n\n" + pick(lang, "welcome_credit",
                          seed=message.from_user.id, credits=credits)
    if is_admin(message.from_user.id):
        body += "\n\n" + pick(lang, "welcome_admin",
                              seed=message.from_user.id)
    send(message.chat.id, body, lang, reply_markup=markup)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    if check_blocked(message):
        return
    ensure_user(message.from_user)
    lang = get_lang(message.from_user.id)
    body = (
        "<b>📖 فەرمانەکان</b>\n\n"
        "/start — دەستپێکردن\n"
        "/help — یارمەتی\n"
        "/id — ناسنامە\n"
        "/lang ku — کوردی\n"
        "/lang en — ئینگلیزی\n\n"
        "<b>بەکارهێنان:</b>\n"
        "نامەیەک بنێرە — بۆتەکە وەڵامت دەداتەوە.\n"
        "هەر نامەیەک = ١ کرێدیت."
    ) if lang == "ku" else (
        "<b>📖 Commands</b>\n\n"
        "/start — start\n"
        "/help — help\n"
        "/id — your ID\n"
        "/lang ku — Kurdish\n"
        "/lang en — English\n\n"
        "<b>Usage:</b>\n"
        "Send a message — the bot replies.\n"
        "Each message = 1 credit."
    )
    send(message.chat.id, body, lang)


@bot.message_handler(commands=["id"])
def cmd_id(message):
    if check_blocked(message):
        return
    ensure_user(message.from_user)
    lang = get_lang(message.from_user.id)
    send(message.chat.id,
         pick(lang, "id_info", seed=message.from_user.id,
              user_id=message.from_user.id), lang)


@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    if check_blocked(message):
        return
    ensure_user(message.from_user)
    current = get_lang(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return send(message.chat.id,
                    pick(current, "lang_usage", seed=message.from_user.id),
                    current)
    choice = parts[1].strip().lower()
    if choice == "ku":
        set_lang(message.from_user.id, "ku")
        return send(message.chat.id,
                    pick("ku", "lang_switched", seed=message.from_user.id),
                    "ku")
    if choice == "en":
        set_lang(message.from_user.id, "en")
        return send(message.chat.id,
                    pick("en", "lang_switched", seed=message.from_user.id),
                    "en")
    send(message.chat.id,
         pick(current, "lang_invalid", seed=message.from_user.id), current)


# ============================================================
# ADMIN HANDLERS
# ============================================================

@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if not is_admin(message.from_user.id):
        return
    lang = get_lang(message.from_user.id)
    bot.send_message(
        message.chat.id,
        pick(lang, "panel_help", seed=message.from_user.id),
        disable_web_page_preview=True,
    )


@bot.message_handler(commands=["system"])
def cmd_system(message):
    if not is_admin(message.from_user.id):
        return
    today = today_str()
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_today = conn.execute(
            "SELECT COUNT(*) FROM users WHERE substr(last_seen,1,10)=?",
            (today,),
        ).fetchone()[0]
        active_week = conn.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE last_seen >= datetime('now','-7 days')"
        ).fetchone()[0]
        banned = conn.execute(
            "SELECT COUNT(*) FROM users WHERE banned_until IS NOT NULL"
        ).fetchone()[0]
        total_req = conn.execute(
            "SELECT COUNT(*) FROM requests"
        ).fetchone()[0]
        credits_left = conn.execute(
            "SELECT COALESCE(SUM(credits),0) FROM users"
        ).fetchone()[0]
    text = (
        "📊 <b>ئاماری سیستەم</b>\n\n"
        f"👥 کۆی بەکارهێنەران: <b>{total}</b>\n"
        f"🟢 چالاک ئەمڕۆ: <b>{active_today}</b>\n"
        f"📅 چالاک ئەم هەفتەیە: <b>{active_week}</b>\n"
        f"🚫 باندکراو: <b>{banned}</b>\n"
        f"💬 کۆی داواکاری: <b>{total_req}</b>\n"
        f"💳 کۆی کرێدیتی ماوە: <b>{credits_left}</b>"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["users"])
def cmd_users(message):
    if not is_admin(message.from_user.id):
        return
    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, first_name, username, credits, last_seen, "
            "       banned_until "
            "FROM users ORDER BY last_seen DESC LIMIT 30"
        ).fetchall()
    if not rows:
        return bot.send_message(message.chat.id, "هیچ بەکارهێنەرێک نییە.")
    lines = ["👥 <b>دوایین ٣٠ بەکارهێنەر</b>\n"]
    for uid, fn, un, credits, ls, ban in rows:
        un_disp = f"@{un}" if un else (fn or "—")
        ban_flag = " 🚫" if ban else ""
        lines.append(
            f"<code>{uid}</code> · {esc(un_disp)} · 💳{credits}{ban_flag}"
        )
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.send_message(
            message.chat.id,
            "شێواز: /ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;",
        )
    try:
        uid = int(parts[1].strip())
    except ValueError:
        return bot.send_message(message.chat.id, "ID هەڵەیە.")
    duration = parts[2].strip().lower()
    if not ban_user(uid, duration):
        return bot.send_message(
            message.chat.id, "ماوە نەناسراوە: forever|1h|1d|7d|30d",
        )
    bot.send_message(
        message.chat.id,
        f"🚫 باند کرا: <code>{uid}</code> ({duration})",
    )


@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.send_message(message.chat.id, "شێواز: /unban &lt;id&gt;")
    try:
        uid = int(parts[1].strip())
    except ValueError:
        return bot.send_message(message.chat.id, "ID هەڵەیە.")
    unban_user(uid)
    bot.send_message(message.chat.id, f"✅ لابرا: <code>{uid}</code>")


def _adjust_credits(message, sign: int, label: str):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.send_message(
            message.chat.id, f"شێواز: /{label} &lt;id&gt; &lt;n&gt;"
        )
    try:
        uid = int(parts[1].strip())
        amount = int(parts[2].strip())
    except ValueError:
        return bot.send_message(message.chat.id, "ID یان ژمارە هەڵەیە.")
    if amount <= 0:
        return bot.send_message(message.chat.id, "ژمارە دەبێت > 0 بێت.")
    with db() as conn:
        row = conn.execute(
            "SELECT credits FROM users WHERE user_id=?", (uid,)
        ).fetchone()
        if not row:
            return bot.send_message(message.chat.id, "بەکارهێنەر نەدۆزرایەوە.")
        new_val = max(0, row[0] + (sign * amount))
        conn.execute(
            "UPDATE users SET credits=? WHERE user_id=?",
            (new_val, uid),
        )
    action = "زیادکرا" if sign > 0 else "کەمکرا"
    bot.send_message(
        message.chat.id,
        f"💳 {action} — <code>{uid}</code> → <b>{new_val}</b>",
    )


@bot.message_handler(commands=["credit"])
def cmd_credit(message):
    _adjust_credits(message, +1, "credit")


@bot.message_handler(commands=["credit2"])
def cmd_credit2(message):
    _adjust_credits(message, -1, "credit2")


@bot.message_handler(commands=["letter"])
def cmd_letter(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return bot.send_message(
            message.chat.id, "شێواز: /letter &lt;text&gt;"
        )
    text = parts[1].strip()
    with db() as conn:
        ids = [r[0] for r in conn.execute(
            "SELECT user_id FROM users"
        ).fetchall()]
    sent = failed = 0
    for uid in ids:
        try:
            bot.send_message(
                uid,
                f"📨 <b>پەیام لە ئەدمین:</b>\n\n{esc(text)}",
            )
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.05)
    bot.send_message(
        message.chat.id,
        f"✅ نێردرا: {sent} · ❌ شکست: {failed}",
    )


@bot.message_handler(commands=["letter2"])
def cmd_letter2(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.send_message(
            message.chat.id, "شێواز: /letter2 &lt;id&gt; &lt;text&gt;"
        )
    try:
        uid = int(parts[1].strip())
    except ValueError:
        return bot.send_message(message.chat.id, "ID هەڵەیە.")
    text = parts[2].strip()
    try:
        bot.send_message(
            uid,
            f"📨 <b>پەیام لە ئەدمین:</b>\n\n{esc(text)}",
        )
        bot.send_message(
            message.chat.id, f"✅ نێردرا بۆ <code>{uid}</code>"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ شکست: {esc(str(e))}")


@bot.message_handler(commands=["history"])
def cmd_history(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.send_message(
            message.chat.id, "شێواز: /history &lt;id&gt;"
        )
    try:
        uid = int(parts[1].strip())
    except ValueError:
        return bot.send_message(message.chat.id, "ID هەڵەیە.")
    rows = get_requests(uid, limit=20)
    if not rows:
        return bot.send_message(message.chat.id, "هیچ داواکارییەک نییە.")
    lines = [f"📜 <b>داواکارییەکانی</b> <code>{uid}</code>\n"]
    for type_, content, created in rows:
        lines.append(
            f"• [{type_}] {created}\n  {esc((content or '')[:200])}"
        )
    bot.send_message(message.chat.id, "\n".join(lines))


# ============================================================
# CHAT + VISION
# ============================================================

@bot.message_handler(content_types=["photo", "document"])
def handle_vision(message):
    if check_blocked(message):
        return
    user_id = message.from_user.id
    ensure_user(message.from_user)
    apply_daily(user_id)
    lang = get_lang(user_id)

    if not is_admin(user_id):
        if rate_limited(user_id):
            return send(message.chat.id,
                        pick(lang, "rate_limited", seed=user_id), lang)
        if not spend_credit(user_id, 1):
            return send(
                message.chat.id,
                pick(lang, "no_credits", seed=user_id,
                     credits=get_credits(user_id)),
                lang,
            )

    file_id = None
    mime = "image/jpeg"
    if message.photo:
        file_id = message.photo[-1].file_id
    elif (message.document
          and (message.document.mime_type or "").startswith("image/")):
        file_id = message.document.file_id
        mime = message.document.mime_type
    if not file_id:
        return

    prompt = (message.caption or "").strip() or pick(
        lang, "vision_default_prompt", seed=user_id
    )
    status = bot.reply_to(message, pick(lang, "vision_ack", seed=user_id))
    stop = threading.Event()
    threading.Thread(
        target=typing_loop, args=(message.chat.id, stop), daemon=True
    ).start()

    try:
        f = bot.get_file(file_id)
        raw = bot.download_file(f.file_path)
        if len(raw) > MAX_IMAGE_BYTES:
            stop.set()
            try:
                bot.delete_message(message.chat.id, status.message_id)
            except Exception:
                pass
            return send(
                message.chat.id,
                pick(lang, "image_too_big", seed=user_id,
                     mb=MAX_IMAGE_BYTES // 1_000_000),
                lang,
            )
        encoded = base64.b64encode(raw).decode("ascii")
        resp = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{mime};base64,{encoded}"
                    }},
                ]},
            ],
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        answer = (resp.choices[0].message.content or "").strip() or pick(
            lang, "no_answer", seed=user_id
        )
        save_message(user_id, "user", "[vision] " + prompt)
        save_message(user_id, "assistant", answer)
        log_request(user_id, "vision", prompt)
        stop.set()
        try:
            bot.delete_message(message.chat.id, status.message_id)
        except Exception:
            pass
        send(message.chat.id, esc(answer), lang,
             reply_to=message.message_id)
    except Exception:
        stop.set()
        log.exception("vision failed")
        try:
            bot.edit_message_text(
                pick(lang, "error_vision", seed=user_id),
                message.chat.id, status.message_id,
            )
        except Exception:
            pass


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bool(m.text) and not m.text.startswith("/"),
)
def handle_chat(message):
    if check_blocked(message):
        return
    user_id = message.from_user.id
    ensure_user(message.from_user)
    apply_daily(user_id)
    lang = get_lang(user_id)

    query = message.text.strip()
    if len(query) > MAX_INPUT_CHARS:
        return send(
            message.chat.id,
            pick(lang, "too_long", seed=user_id, limit=MAX_INPUT_CHARS),
            lang,
        )

    if not is_admin(user_id):
        if rate_limited(user_id):
            return send(message.chat.id,
                        pick(lang, "rate_limited", seed=user_id), lang)
        if not spend_credit(user_id, 1):
            return send(
                message.chat.id,
                pick(lang, "no_credits", seed=user_id,
                     credits=get_credits(user_id)),
                lang,
            )

    status = bot.reply_to(message, pick(lang, "thinking", seed=user_id))
    stop = threading.Event()
    threading.Thread(
        target=typing_loop, args=(message.chat.id, stop), daemon=True
    ).start()

    try:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(get_history(user_id, limit=HISTORY_LIMIT))
        msgs.append({"role": "user", "content": query})
        answer = call_ai(msgs)
        save_message(user_id, "user", query)
        save_message(user_id, "assistant", answer)
        log_request(user_id, "chat", query)
        stop.set()
        try:
            bot.delete_message(message.chat.id, status.message_id)
        except Exception:
            pass
        send(message.chat.id, esc(answer), lang,
             reply_to=message.message_id)
    except Exception:
        stop.set()
        log.exception("chat failed")
        try:
            bot.edit_message_text(
                pick(lang, "error_api", seed=user_id),
                message.chat.id, status.message_id,
            )
        except Exception:
            pass


@bot.message_handler(
    content_types=["text"],
    func=lambda m: bool(m.text) and m.text.startswith("/"),
)
def handle_unknown(message):
    if is_admin(message.from_user.id):
        return
    if check_blocked(message):
        return
    ensure_user(message.from_user)
    lang = get_lang(message.from_user.id)
    send(message.chat.id,
         pick(lang, "unknown_command", seed=message.from_user.id), lang)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    init_db()
    log.info("booting BLACK HAT AI PRIME")
    log.info("admins: %s", sorted(ADMIN_IDS))
    log.info("start=%d daily=%d", STARTING_CREDITS, DAILY_CREDITS)
    log.info("banks: ku=%d cats, en=%d cats",
             len(BANK["ku"]), len(BANK["en"]))

    try:
        try:
            bot.remove_webhook()
        except Exception:
            pass
        bot.infinity_polling(
            skip_pending=True, timeout=20, long_polling_timeout=20
        )
    except Exception:
        log.exception("polling crashed")
    finally:
        log.info("stopped")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        log.exception("fatal")
        sys.exit(5)
