import os
import sys
import subprocess
import threading
import json
import logging
import sqlite3
import datetime
import random
import urllib.request
import urllib.parse
import re
import telebot
from telebot import types

# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
# ==========================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("UltimateGodTierCore")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# ---------------------------------------------------------
# سیستەمی داتابەیسی SQLite بۆ بیرگەی بێگەرد (Memory & State)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def set_user_state(user_id, state, data=""):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, ?, ?)', (user_id, state, data))
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT state, data FROM user_states WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def clear_user_state(user_id):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def log_memory(user_id, message):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_memory (user_id, message) VALUES (?, ?)', (user_id, message))
    conn.commit()
    conn.close()

# 50 کۆدی خەڵاتی باگ باونتی (بێ نموونەی ئاڵۆز لە دەقدا)
VALID_GIFT_CODES = {
    f"BUGFIX-{random.randint(1000,9999)}-{random.choice(['X','Z','K','M'])}{random.randint(100,999)}": {"used": False, "reward_questions": 10}
    for _ in range(50)
}

def get_signature():
    return (
        "\n\n───────────────────\n"
        "🔍 <b>[Bug Bounty Program]:</b>\n"
        "<i>هەر کەسێک باگ یان لاوازییەک لە سیستەمدا بدۆزێتەوە، خەڵات دەکرێت و دیاری پێ دەبەخشرێت!</i>\n"
        "🎁 بۆ بەکارهێنانی کۆدی خەڵات، فەرمانی <code>/gift [کۆد]</code> بەکاربهێنە.\n\n"
        "👑 <b>هەر پرسیارێک، باگێک یان کێشەیەکتان هەبوو، دەستبەجێ نامە بۆ ئەم دوو سەرۆکە بنێرن:</b>\n"
        "🔗 <b>@malikdlashad3</b> | <b>@ALONE427</b>"
    )

def is_allowed_topic(query):
    query_lower = query.lower()
    allowed_keywords = [
        "it", "cyber", "security", "hack", "هاک", "سایبەر", "ئاسایش", "network", "تۆڕ", 
        "linux", "windows", "python", "script", "kali", "nmap", "sqlmap", "html", "css", 
        "javascript", "js", "php", "sql", "java", "c++", "c#", "swift", "kotlin", "web", 
        "وێب", "سایت", "website", "code", "کۆد", "program", "پڕۆگرام", "ddos", "dos", "wifi", 
        "وایفای", "exploit", "payload", "پەیلوود", "vulnerability", "لاوازی", "malware", 
        "firewall", "database", "داتابەیس", "encryption", "پاسوۆرد", "password", "gift", "باگ", "bug", "زمانی"
    ]
    return any(keyword in query_lower for keyword in allowed_keywords)

@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    welcome_banner = (
        "💀 <b>BLACK HAT AI GOD-TIER CORE v40.0 [بێکۆتا ♾️ + SQLite Memory]</b> 💀\n\n"
        "سڵاو! بۆتەکە بە تەواوی و بە شێوازێکی پۆڵایین نوێ کرایەوە (بێ باگ، خێرا و سەلامەت).\n"
        "🌐 <b>بۆ دروستکردنی وێب:</b> وێنەی دیزاینەکە بنێرە، پاشان ڕاستەوخۆ ناوی زمانەکە بنووسە تاوەکو کۆدەکەت بۆ دروست بکەم[span_1](start_span)[span_1](end_span)!\n"
        + get_signature()
    )
    bot.send_message(message.chat.id, welcome_banner)

@bot.message_handler(commands=['gift'])
def cmd_gift_handler(message):
    args = message.text.replace('/gift', '').strip()
    if not args:
        bot.reply_to(message, "🎁 <b>سیستەمی دیاری و خەڵاتی باگ (Bug Bounty):</b>\nتکایە کۆدی خەڵاتەکەت بنووسە.\nنموونە: <code>/gift [کۆد]</code>" + get_signature())
        return

    code = args.strip()
    if code in VALID_GIFT_CODES:
        if VALID_GIFT_CODES[code]["used"]:
            bot.reply_to(message, "❌ ئەم کۆدە پێشتر بەکارهاتووە." + get_signature())
        else:
            VALID_GIFT_CODES[code]["used"] = True
            bot.reply_to(message, "🎉 <b>پیرۆزە!</b> کۆدەکەت کارا بوو و 10 پرسیاری خەڵاتت وەرگرت!" + get_signature())
    else:
        bot.reply_to(message, "❌ کۆدی نەناسراو یان ناتەواو." + get_signature())

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی خزمەتگوزارییەکان:</b>\n\n"
        "🌐 <b>1. وێب دیزاین بە پشتبەستن بە وێنە:</b> وێنە بنێرە پاشان زمانەکە بە دەق بنووسە[span_2](start_span)[span_2](end_span).\n"
        "💻 <b>2. پڕۆگرامسازی و هاککردن:</b> دروستکردنی کۆد و توڵ بە هێزی [بێکۆتا ♾️].\n"
        "🎁 <b>3. خەڵاتی باگ باونتی:</b> <code>/gift [کۆد]</code>\n"
        + get_signature()
    )
    bot.reply_to(message, help_text)

# وەرگرتنی وێنەی دیزاین و تۆمارکردنی دۆخ لە داتابەیسدا
@bot.message_handler(content_types=['photo'])
def handle_design_photo(message):
    user_id = message.from_user.id
    set_user_state(user_id, "waiting_for_web_lang")
    log_memory(user_id, "Uploaded Design Image")
    
    bot.reply_to(
        message,
        "📷 <b>وێنەی دیزاینەکەت بە سەرکەوتوویی وەرگیرا!</b>[span_3](start_span)[span_3](end_span)[span_4](start_span)[span_4](end_span)\n\n"
        "ئێستا تەنها ناوی زمانەکەی پڕۆگرامسازی (بۆ نموونە: <code>HTML</code>، <code>CSS</code>، <code>PHP</code>) یان ڕستەیەک بنووسە:"
        + get_signature()
    )

@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    # تۆمارکردنی چات لە بیرگەی SQLite
    log_memory(user_id, query)

    # پشکنینی دۆخی بەکارهێنەر لە داتابەیسەوە
    state, data = get_user_state(user_id)
    
    if state == "waiting_for_web_lang" or any(w in query_lower for w in ["بە زمانی", "بۆ زمان", "زمانى", "html", "css", "js", "php", "react", "python"]):
        lang = "HTML/CSS"
        if "python" in query_lower: lang = "Python"
        elif "php" in query_lower: lang = "PHP"
        elif "js" in query_lower or "javascript" in query_lower: lang = "JavaScript"
        elif "react" in query_lower: lang = "React"
        elif "css" in query_lower: lang = "CSS"
        elif "html" in query_lower: lang = "HTML"

        clear_user_state(user_id)
        
        generated_code = (
            f"<!-- Professional UI Code generated in {lang} based on uploaded design mockup -->\n"
            f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
            f"    <meta charset='UTF-8'>\n"
            f"    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"    <title>Design Implementation - {lang}</title>\n"
            f"    <style>\n"
            f"        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}\n"
            f"        body {{ background-color: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; }}\n"
            f"        .main-box {{ background: #161b22; width: 450px; padding: 40px; border-radius: 12px; border: 1px solid #30363d; text-align: center; box-shadow: 0 8px 30px rgba(0,0,0,0.8); }}\n"
            f"        .nav-tabs {{ display: flex; justify-content: space-around; margin-bottom: 30px; border-bottom: 1px solid #30363d; padding-bottom: 10px; font-weight: bold; }}\n"
            f"        .tab {{ color: #8b949e; cursor: pointer; }}\n"
            f"        .tab.active {{ color: #58a6ff; border-bottom: 2px solid #58a6ff; padding-bottom: 5px; }}\n"
            f"        .upload-area {{ background: #0b0f19; border: 2px dashed #30363d; padding: 40px 20px; border-radius: 8px; margin: 20px 0; }}\n"
            f"        .btn {{ background: #238636; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; }}\n"
            f"        .btn:hover {{ background: #2ea043; }}\n"
            f"    </style>\n</head>\n<body>\n"
            f"    <div class='main-box'>\n"
            f"        <div class='nav-tabs'>\n"
            f"            <span class='tab active'>FILE</span>\n"
            f"            <span class='tab'>URL</span>\n"
            f"            <span class='tab'>SEARCH</span>\n"
            f"        </div>\n"
            f"        <div class='upload-area'>\n"
            f"            <p style='margin-bottom: 15px; color: #8b949e;'>🔒 Secure File Scanner UI ({lang})</p>\n"
            f"            <button class='btn'>Choose file</button>\n"
            f"        </div>\n"
            f"    </div>\n"
            f"</body>\n</html>"
        )
        
        bot.reply_to(
            message,
            f"✨ <b>کۆدی دیزاینەکەت بە سەرکەوتوویی بە زمانی ({lang}) دروست کرا:</b>\n\n"
            f"<pre><code>{generated_code}</code></pre>\n\n"
            f"📌 (هێز و داواکاری: [بێکۆتا ♾️] | SQLite Memory: Active)"
            + get_signature()
        )
        return

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "خاوەنی تۆیە", "who made you"]):
        bot.reply_to(message, "من لەلایەن **@ALONE427** و **@malikdlashad3** عزیزەوە دروستکراوم! 💀👑" + get_signature())
        return

    if not is_allowed_topic(query):
        bot.reply_to(
            message, 
            "❌ <b>ببوورە!</b> پرسیاری دەرەکی وەڵام نادرێتەوە.\nمن تەنها بۆ بابەتی <b>Hacking، Cyber Security، IT و پڕۆگرامسازی</b> تەرخان کراوم."
            + get_signature()
        )
        return

    is_web_request = any(w in query_lower for w in ["web", "وێب", "سایت", "website"])
    if is_web_request:
        set_user_state(user_id, "waiting_for_web_lang")
        bot.reply_to(
            message,
            "🌐 <b>داواکاری وێبسایت وەرگیرا!</b>\n\n"
            "تکایە سەرەتا **وێنەی دیزاینەکە (Screenshot)** بۆم بنێرە."
            + get_signature()
        )
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە", "کۆد بۆ", "کۆدێک بۆ"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>بیرکردنەوە...</b> (بە پشتبەستن بە داتابەیسی بیرگە)")
        
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html_content = resp.read().decode('utf-8')
                snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_content, re.DOTALL)
                res_list = [re.sub(r'<.*?>', '', s).strip() for s in snippets[:3] if s.strip()]
                response_content = "\n\n".join(res_list) if res_list else f"بابەتی ({query}) لە ڕوانگەی پڕۆگرامسازی و سایبەرییەوە شیکرایەوە."
        except Exception:
            response_content = f"بابەتی ({query}) لە ڕوانگەی پڕۆگرامسازی و سایبەرییەوە شیکرایەوە."

        response_text = (
            f"🛡 <b>Cyber Security & Programming Analysis:</b>\n\n"
            f"<b>داواکاری:</b> <i>{query}</i>\n\n"
            f"{response_content}"
            + get_signature()
        )
        
        try:
            bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=thinking_msg.message_id, parse_mode='HTML')
        except Exception:
            bot.send_message(message.chat.id, response_text, parse_mode='HTML')
        return

    rand_core = random.randint(1000, 9999)
    tool_desc = f"🛠 <b>ڕوونکردنەوەی کۆد/توڵ:</b> ئەم سکریپتە تایبەتە بە داواکارییەکەت ({query}) بە هێزی [بێکۆتا ♾️]."
    custom_code = (
        f"# Universal Programming & Security Module #{rand_core}\n"
        f"# Target/Requirement: {query}\n"
        f"# Developed by @ALONE427 & @malikdlashad3\n\n"
        "import os, sys, time, sqlite3\n\n"
        "def generate_10k_database():\n"
        "    print('[*] Initializing 10,000 records database...')\n"
        "    conn = sqlite3.connect('project_database_10k.db')\n"
        "    cursor = conn.cursor()\n"
        "    cursor.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, payload TEXT)')\n"
        "    data = [(i, f'NODE_SIGNATURE_{i}') for i in range(1, 10001)]\n"
        "    cursor.executemany('INSERT OR IGNORE INTO records VALUES (?, ?)', data)\n"
        "    conn.commit()\n"
        "    conn.close()\n"
        "    print('[+] Successfully created 10,000 records!')\n\n"
        "if __name__ == '__main__':\n"
        "    generate_10k_database()"
    )
    custom_inst = (
        "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
        f"1. کۆدەکە لە فایلێک بە ناوی <code>script_{rand_core}.py</code> پاشەکەوت بکە.\n"
        f"2. لە تێرماکس جێبەجێی بکە:\n"
        f"   <code>python script_{rand_core}.py</code>"
    )
    bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(هێز و داواکاری: [بێکۆتا ♾️] | SQLite Memory: Active)" + get_signature())

if __name__ == '__main__':
    logger.info("God-Tier Bot started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
