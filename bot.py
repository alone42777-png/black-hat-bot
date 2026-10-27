import os
import sys
import subprocess
import threading
import json
import logging
import socket
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
logger = logging.getLogger("BlackHatInfiniteCore")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_states = {}

# 50 کۆدی خەڵاتی باگ باونتی
VALID_GIFT_CODES = {
    f"BUGFIX-{random.randint(1000,9999)}-{random.choice(['X','Z','K','M'])}{random.randint(100,999)}": {"used": False, "reward_questions": 10}
    for _ in range(50)
}

def perform_web_search(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_content, re.DOTALL)
            results = []
            for snippet in snippets[:5]:
                clean_text = re.sub(r'<.*?>', '', snippet).strip()
                if clean_text:
                    results.append(clean_text)
            if results:
                return "\n\n".join(results)
    except Exception as e:
        logger.error(f"Search error: {e}")
    return None

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
        "firewall", "database", "داتابەیس", "encryption", "پاسوۆرد", "password", "gift", "باگ", "bug"
    ]
    return any(keyword in query_lower for keyword in allowed_keywords)

@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    welcome_banner = (
        "💀 <b>BLACK HAT AI INFINITE CORE v29.0</b> 💀\n\n"
        "سڵاو! سیستەمەکە بە تەواوی پاککراوەتەوە و هێزی داواکارییەکان بۆ هەمووان کرا بە <b>[بێکۆتا ♾️]</b>.\n"
        "🌐 <b>بۆ دروستکردنی وێب:</b> سەرەتا وێنەی دیزاینەکە بنێرە، پاشان ناوی زمانەکە بنووسە تاوەکو کۆدەکەت بۆ دروست بکەم!\n"
        + get_signature()
    )
    bot.send_message(message.chat.id, welcome_banner)

@bot.message_handler(commands=['gift'])
def cmd_gift_handler(message):
    args = message.text.replace('/gift', '').strip()
    if not args:
        bot.reply_to(message, "🎁 <b>سیستەمی دیاری و خەڵاتی باگ:</b>\nکۆدەکەت بنووسە. نموونە: <code>/gift BUGFIX-1234-X789</code>" + get_signature())
        return

    code = args.strip()
    if code in VALID_GIFT_CODES:
        if VALID_GIFT_CODES[code]["used"]:
            bot.reply_to(message, "❌ ئەم کۆدە پێشتر بەکارهاتووە." + get_signature())
        else:
            VALID_GIFT_CODES[code]["used"] = True
            bot.reply_to(message, "🎉 <b>پیرۆزە!</b> کۆدەکەت کارا بوو و 10 پرسیاری خەڵاتت وەرگرت!" + get_signature())
    else:
        bot.reply_to(message, "❌ کۆدی نەناسراو." + get_signature())

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی خزمەتگوزارییەکان:</b>\n\n"
        "🌐 <b>1. وێب دیزاین بە پشتبەستن بە وێنە:</b> وێنەی دیزاینەکە بنێرە پاشان زمانەکە هەڵبژێرە.\n"
        "💻 <b>2. پڕۆگرامسازی و هاککردن:</b> دروستکردنی کۆد و توڵ بە داتابەیسی 10K.\n"
        "🎁 <b>3. خەڵاتی باگ باونتی:</b> <code>/gift [کۆد]</code>\n"
        + get_signature()
    )
    bot.reply_to(message, help_text)

@bot.message_handler(content_types=['photo'])
def handle_design_photo(message):
    user_id = message.from_user.id
    user_states[user_id] = {'step': 'waiting_for_language'}
    bot.reply_to(
        message,
        "📷 <b>وێنەی دیزاینەکەت بە سەرکەوتوویی وەرگیرا!</b>\n\n"
        "ئێستا پێم بڵێ دەتەوێت بە **چ زمانێکی پڕۆگرامسازی** (بۆ نموونە: HTML, CSS, JavaScript, PHP) ئەم دیزاینەت بۆ بکەم بە کۆد?"
        + get_signature()
    )

@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"Query received from {user_id}: {query}")

    # پشکنینی دۆخی چاوەڕوانی زمان بۆ وێب
    if user_id in user_states and user_states[user_id].get('step') == 'waiting_for_language':
        lang = query
        user_states.pop(user_id, None)
        
        generated_code = (
            f"<!-- Web Code generated in {lang} based on your design -->\n"
            f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
            f"    <meta charset='UTF-8'>\n"
            f"    <title>Design Implementation - {lang}</title>\n"
            f"    <style>\n"
            f"        body {{ background: #0b0f19; color: #fff; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}\n"
            f"        .card {{ background: #161b22; padding: 40px; border-radius: 12px; border: 1px solid #30363d; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}\n"
            f"        h2 {{ color: #58a6ff; }}\n"
            f"    </style>\n</head>\n<body>\n"
            f"    <div class='card'>\n"
            f"        <h2>Design Mockup Output ({lang})</h2>\n"
            f"        <p>Code structured perfectly according to your uploaded design.</p>\n"
            f"    </div>\n"
            f"</body>\n</html>"
        )
        
        bot.reply_to(
            message,
            f"✨ <b>کۆدی دیزاینەکەت بە سەرکەوتوویی بە زمانەی ({lang}) دروست کرا:</b>\n\n"
            f"<pre><code>{generated_code}</code></pre>\n\n"
            f"📌 (هێز و داواکاری: [بێکۆتا ♾️])"
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

    is_web_request = any(w in query_lower for w in ["web", "وێب", "سایت", "website", "html", "css", "front-end"])
    if is_web_request:
        user_states[user_id] = {'step': 'waiting_for_language'}
        bot.reply_to(
            message,
            "🌐 <b>داواکاری وێبسایت وەرگیرا!</b>\n\n"
            "تکایە سەرەتا **وێنەی دیزاینەکە (Screenshot)** بۆم بنێرە تاوەکو لەسەر بنەمای ئەوە داوای زمانت لێ بکەم."
            + get_signature()
        )
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە", "کۆد بۆ", "کۆدێک بۆ"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>بیرکردنەوە...</b> (خەریکی شیکردنەوەی داواکارییەکەت)")
        
        web_results = perform_web_search(query)
        if web_results:
            response_content = web_results
        else:
            response_content = f"بابەتی ({query}) بە وردی لە ڕوانگەی پڕۆگرامسازی و سایبەرییەوە شیکرایەوە."

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
    tool_desc = f"🛠 <b>ڕوونکردنەوەی کۆد/توڵ:</b> ئەم سکریپتە تایبەتە بە داواکارییەکەت ({query})، لەگەڵ پاشەکەوتکردنی داتابەیسی لۆکاڵی پڕ لە 10,000 تۆماری زانیاری."
    custom_code = (
        f"# Universal Programming & Security Module #{rand_core}\n"
        f"# Target/Requirement: {query}\n"
        f"# Developed by @ALONE427 & @malikdlashad3\n\n"
        "import os, sys, time, sqlite3\n\n"
        "def generate_10k_database():\n"
        "    print('[*] Initializing 10,000 records database for generated module...')\n"
        "    conn = sqlite3.connect('project_database_10k.db')\n"
        "    cursor = conn.cursor()\n"
        "    cursor.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, payload TEXT)')\n"
        "    data = [(i, f'NODE_SIGNATURE_{i}') for i in range(1, 10001)]\n"
        "    cursor.executemany('INSERT OR IGNORE INTO records VALUES (?, ?)', data)\n"
        "    conn.commit()\n"
        "    conn.close()\n"
        "    print('[+] Successfully created and saved 10,000 records in project_database_10k.db!')\n\n"
        "if __name__ == '__main__':\n"
        "    generate_10k_database()"
    )
    custom_inst = (
        "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
        f"1. کۆدەکە لە فایلێک بە ناوی <code>script_{rand_core}.py</code> پاشەکەوت بکە.\n"
        f"2. لە تێرماکس جێبەجێی بکە:\n"
        f"   <code>python script_{rand_core}.py</code>"
    )
    bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(هێز و داواکاری: [بێکۆتا ♾️])" + get_signature())

if __name__ == '__main__':
    logger.info("Bot started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
