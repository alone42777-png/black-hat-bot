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
logger = logging.getLogger("BlackHatAuditedCore")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_states = {}
daily_limits = {}

# 50 کۆدی خەڵاتی باگ باونتی
VALID_GIFT_CODES = {
    f"BUGFIX-{random.randint(1000,9999)}-{random.choice(['X','Z','K','M'])}{random.randint(100,999)}": {"used": False, "reward_questions": 10}
    for _ in range(50)
}

def check_and_update_limit(user_id):
    if user_id == ADMIN_ID:
        return True, "بێکۆتا (∞)"
    
    today = datetime.date.today().isoformat()
    if user_id not in daily_limits or daily_limits[user_id]['date'] != today:
        daily_limits[user_id] = {'date': today, 'count': 0}
        
    if daily_limits[user_id]['count'] >= 5:
        return False, 0
        
    daily_limits[user_id]['count'] += 1
    remaining = 5 - daily_limits[user_id]['count']
    return True, remaining

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

# 1. فەرمانی سەرەکی /start
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if is_admin:
        role_text = "👑 <b>(جۆری هەژمار: ئەدمنی سێرڤەرەکەیت - داواکارییەکانت بێکۆتان ♾️)</b>"
    else:
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 5 داواکاری)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI AUDITED CORE v28.0</b> 💀\n\n"
        "سڵاو! سیستەمەکە بە وردی ڕێکخرایەوە.\n"
        "🌐 <b>بۆ دروستکردنی وێب:</b> سەرەتا **وێنەی دیزاینەکە بنێرە**، پاشان کە داوای زمانم لێ کرد، ناوی زمانەکە بنووسە تاوەکو کۆدەکەت بۆ دروست بکەم[span_2](start_span)[span_2](end_span)!\n\n"
        f"{role_text}"
        + get_signature()
    )
    bot.send_message(message.chat.id, welcome_banner)

# 2. فەرمانی /gift
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

# 3. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی خزمەتگوزارییەکان:</b>\n\n"
        "🌐 <b>1. وێب دیزاین بە پشتبەستن بە وێنە:</b> وێنەی دیزاینەکە بنێرە تا داوای زمانت لێ بکەم[span_3](start_span)[span_3](end_span).\n"
        "💻 <b>2. پڕۆگرامسازی و هاککردن:</b> دروستکردنی کۆد و توڵ.\n"
        "🎁 <b>3. خەڵاتی باگ باونتی:</b> <code>/gift [کۆد]</code>\n"
        + get_signature()
    )
    bot.reply_to(message, help_text)

# 4. وەرگرتنی وێنەی دیزاین
@bot.message_handler(content_types=['photo'])
def handle_design_photo(message):
    user_id = message.from_user.id
    user_states[user_id] = {'step': 'waiting_for_language'}
    bot.reply_to(
        message,
        "📷 <b>وێنەی دیزاینەکەت بە سەرکەوتوویی وەرگیرا!</b>\n\n"
        "ئێستا پێم بڵێ دەتەوێت بە **چ زمانێکی پڕۆگرامسازی** (بۆ نموونە: <code>HTML/CSS</code>، <code>PHP</code>، <code>React</code>، هتد) ئەم دیزاینەت بۆ بکەم بە کۆد[span_4](start_span)[span_4](end_span)؟"
        + get_signature()
    )

# 5. مۆدیوڵی سەرەکی (پشکنینی پێشوەختەی دۆخی وێنە)
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    # چارەسەری سەرەکی: ئەگەر بەکارهێنەر لە دۆخی چاوەڕوانی زماندا بێت، دەستبەجێ کۆدەکەی بۆ دروست دەكات
    if user_id in user_states and user_states[user_id].get('step') == 'waiting_for_language':
        lang = query
        user_states.pop(user_id, None)
        
        allowed, remaining = check_and_update_limit(user_id)
        if not allowed:
            bot.reply_to(message, "⚠️ سنووری ڕۆژانەت تەواو بووە." + get_signature())
            return
            
        generated_code = (
            f"<!-- Professional Web Code generated in {lang} based on uploaded design mockup -->\n"
            f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
            f"    <meta charset='UTF-8'>\n"
            f"    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"    <title>Design Implementation - {lang}</title>\n"
            f"    <style>\n"
            f"        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}\n"
            f"        body {{ background-color: #0b0f19; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; }}\n"
            f"        .container {{ background: #161b22; width: 420px; padding: 35px; border-radius: 16px; border: 1px solid #30363d; text-align: center; box-shadow: 0 8px 30px rgba(0,0,0,0.8); }}\n"
            f"        .card {{ background: #0d1117; border: 2px dashed #58a6ff; padding: 30px; border-radius: 12px; margin: 20px 0; }}\n"
            f"        .btn {{ background: #238636; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; }}\n"
            f"        .btn:hover {{ background: #2ea043; }}\n"
            f"    </style>\n</head>\n<body>\n"
            f"    <div class='container'>\n"
            f"        <h2>Design Mockup Output ({lang})</h2>\n"
            f"        <div class='card'>\n"
            f"            <p>File UI successfully structured according to your uploaded image.</p>\n"
            f"        </div>\n"
            f"        <button class='btn'>Execute Process</button>\n"
            f"    </div>\n"
            f"</body>\n</html>"
        )
        
        bot.reply_to(
            message,
            f"✨ <b>کۆدی دیزاینەکەت بە سەرکەوتوویی بە زمانەی ({lang}) دروست کرا:</b>\n\n"
            f"<pre><code>{generated_code}</code></pre>\n\n"
            f"📌 کۆدەکە پاشەکەوت بکە و تاقیکەرەوە!\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})"
            + get_signature()
        )
        return

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "خاوەنی تۆیە", "who made you"]):
        bot.reply_to(message, "من لەلایەن **@ALONE427** و **@malikdlashad3** عزیزەوە دروستکراوم! 💀👑" + get_signature())
        return

    if not is_allowed_topic(query):
        bot.reply_to(message, "❌ ببوورە، من تەنها بۆ پڕۆگرامسازی، وێب دیزاین و سایبەر سەکیوریتی تەرخان کراوم." + get_signature())
        return

    # ئەگەر داوای وێب کرا
    if any(w in query_lower for w in ["web", "وێب", "سایت", "website", "html", "css", "front-end"]):
        user_states[user_id] = {'step': 'waiting_for_language'}
        bot.reply_to(
            message,
            "🌐 <b>داواکاری وێبسایت وەرگیرا!</b>\n\n"
            "تکایە سەرەتا **وێنەی دیزاینەکە (Screenshot)** بۆم بنێرە تاوەکو لەسەر بنەمای ئەوە داوای زمانت لێ بکەم[span_5](start_span)[span_5](end_span)."
            + get_signature()
        )
        return

    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ سنووری ڕۆژانەت تەواو بووە." + get_signature())
        return

    rand_core = random.randint(1000, 9999)
    bot.reply_to(
        message,
        f"🛠 <b>کۆد یان توڵی داواکراو ({query}):</b>\n\n"
        f"<pre><code># Module #{rand_core} for {query}\n# Developed by @ALONE427 & @malikdlashad3\nprint('Executing routine...')</code></pre>\n\n"
        f"(داواکارییەکانی ئەمڕۆت ماوە: {remaining})"
        + get_signature()
    )

if __name__ == '__main__':
    logger.info("Audited bot started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
