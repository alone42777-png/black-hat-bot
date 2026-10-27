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
logger = logging.getLogger("BlackHatUniversalCore")

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

# ڕێگەدان بە هەموو زمانەکانی پڕۆگرامسازی، تەکنیۆلۆجی، وێب و هاککردن
def is_allowed_topic(query):
    query_lower = query.lower()
    allowed_keywords = [
        "it", "cyber", "security", "hack", "هاک", "سایبەر", "ئاسایش", "network", "تۆڕ", 
        "linux", "windows", "python", "script", "kali", "nmap", "sqlmap", "html", "css", 
        "javascript", "js", "php", "sql", "java", "c++", "c#", "swift", "kotlin", "web", 
        "وێب", "سایت", "website", "code", "کۆد", "program", "پڕۆگرام", "ddos", "dos", "wifi", 
        "وایفای", "exploit", "payload", "پەیلوود", "vulnerability", "لاوازی", "malware", 
        "firewall", "database", "داتابەیس", "encryption", "پاسوۆرد", "password", "gift", "کۆد", "باگ", "bug"
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
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 5 داواکاری بۆ توڵ و پڕۆگرامسازی)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI UNIVERSAL CORE v26.0</b> 💀\n\n"
        "سڵاو! من زیرەکییەکی دەستکردم و بۆت هەموو زمانەکانی پڕۆگرامسازی، وێب دیزاین و ئاسایشی سایبەری ئامادەم.\n"
        "🌐 <i>ئەگەر داوای دروستکردنی وێب (Web) بکەیت، سەرەتا داوای دیزاینەکەی بە وێنە و شێوازی بینکاری دەکەم!</i>\n\n"
        f"{role_text}"
        + get_signature()
    )
    
    bot.send_message(message.chat.id, welcome_banner)

# 2. فەرمانی /gift بۆ پشکنینی کۆدی خەڵاتی باگ
@bot.message_handler(commands=['gift'])
def cmd_gift_handler(message):
    args = message.text.replace('/gift', '').strip()
    if not args:
        bot.reply_to(message, "🎁 <b>سیستەمی دیاری و خەڵاتی دۆزینەوەی باگ (Bug Bounty):</b>\nتکایە کۆدی خەڵاتەکەت لەگەڵ فەرمانەکە بنووسە.\nنموونە: <code>/gift BUGFIX-1234-X789</code>" + get_signature())
        return

    code = args.strip()
    if code in VALID_GIFT_CODES:
        if VALID_GIFT_CODES[code]["used"]:
            bot.reply_to(message, "❌ <b>ببوورە!</b> ئەم کۆدی خەڵاتە پێشتر بەکارهاتووە و تەنها یەکجار کارا دەبێت." + get_signature())
        else:
            VALID_GIFT_CODES[code]["used"] = True
            questions_count = VALID_GIFT_CODES[code]["reward_questions"]
            bot.reply_to(message, f"🎉 <b>پیرۆزە!</b> کۆدەکەت بە سەرکەوتوویی کارا بوو.\n🎁 تۆ شایستەی خەڵات و دیاری بوویت بۆ دۆزینەوەی باگ لە سیستەمدا.\n✨ بڕی خەڵات: <b>{questions_count} پرسیاری تایبەت و خەڵاتکراو</b> چالاک کرا!" + get_signature())
    else:
        bot.reply_to(message, "❌ <b>هەڵە!</b> کۆدی باگی ناتەواو یان نەناسراو." + get_signature())

# 3. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Directory):</b>\n\n"
        "🌐 <b>1. بەشی پڕۆگرامسازی و دروستکردنی وێب (Web & Coding):</b>\n"
        "• HTML, CSS, JavaScript, Python, PHP, SQL و هەموو زمانەکانی تر.\n"
        "• سیستەمی داواکردنی وێنە و دیزاینی وێب پێش نووسینی کۆد.\n\n"
        "💥 <b>2. بەشی هاککردن و ئاسایش (Hacking & Security):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت.\n"
        "• Sqlmap, Hydra, Wi-Fi Tools, DDoS Suites.\n\n"
        "🎁 <b>3. بەشی دیاری و خەڵاتی باگ (Bug Bounty):</b>\n"
        "• <code>/gift [کۆد]</code> - بەکارهێنانی کۆدی خەڵات.\n\n"
        + get_signature()
    )
    bot.reply_to(message, help_text)

# 4. ئامرازی Nmap
@bot.message_handler(commands=['nmap'])
def ai_nmap_handler(message):
    user_id = message.from_user.id
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد." + get_signature())
        return

    target = message.text.replace('/nmap', '').strip()
    if not target:
        bot.reply_to(message, "⚠️ تکایە ئایپی یان دۆمەین بنووسە. بۆ نموونە: <code>/nmap 127.0.0.1</code>" + get_signature())
        return
        
    bot.reply_to(message, f"⏳ سکانکردن دەستی پێکرد بۆ ئامانج: <b>{target}</b> ... (ماوەی ئەمڕۆت: {remaining})")
    try:
        cmd = f"nmap -sV -T4 --top-ports 50 {target}"
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        res = output.decode('utf-8', errors='ignore')
        if len(res) > 4000:
            res = res[:4000] + "\n[Output Truncated...]"
        bot.send_message(message.chat.id, f"📊 <b>Nmap Results:</b>\n<pre>{res}</pre>" + get_signature())
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە ئەنجامدانی سکان: {e}" + get_signature())

# 5. فەرمانی شێڵ (/sh)
@bot.message_handler(commands=['sh'])
def ai_shell_handler(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.reply_to(message, "⛔ تەنها ئەدمن دەسەڵاتی جێبەجێکردنی فەرمانی شێڵی هەیە." + get_signature())
        return

    cmd = message.text.replace('/sh', '').strip()
    if not cmd:
        bot.reply_to(message, "⚠️ تکایە فەرمانێک بنووسە. بۆ نموونە: <code>/sh pkg update</code>" + get_signature())
        return
        
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=20)
        res = output.decode('utf-8', errors='ignore')
        if len(res) > 4000:
            res = res[:4000] + "\n[Truncated...]"
        bot.send_message(message.chat.id, f"⚡ <b>Shell Execution:</b>\n<pre>{res}</pre>" + get_signature())
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە جێبەجێکردندا: {e}" + get_signature())

# 6. مۆدیوڵی سەرەکی (پشتیوانی لە هەموو زمانەکانی پۆگرامسازی و داواکردنی دیزاینی وێب بە وێنە)
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"AI Query received from {user_id}: {query}")

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "کێ خاوەنی تۆیە", "خاوەنەکەت کێیە", "سەرۆکەکەت کێیە", "who made you", "who is your boss", "دروستکەرت کێیە", "بەرپرست کێیە"]):
        bot.reply_to(message, "من لەلایەن **@ALONE427** و **@malikdlashad3** عزیزەوە دروستکراوم و ئەوان خاوەن و سەرۆکە بەڕێزەکانی منن! 💀👑" + get_signature())
        return

    if not is_allowed_topic(query):
        refusal_msg = (
            "❌ <b>ببوورە!</b> ئەم بابەتە لە دەرەوەی توانا و پۆلێنکردنی منە.\n"
            "من تەنها بۆ پڕۆگرامسازی، زمانەکانی کۆدکردن، وێب دیزاین، IT و Cyber Security تەرخان کراوم."
            + get_signature()
        )
        bot.reply_to(message, refusal_msg)
        return

    # پشکنینی ئەوەی ئایا داوای دروستکردنی وێب (Web Site) کراوە
    is_web_request = any(w in query_lower for w in ["web", "وێب", "سایت", "website", "html", "css", "front-end", "landing page"])
    if is_web_request:
        web_flow_msg = (
            "🌐 <b>سیستەمی دروستکردنی وێب (Web Development Flow):</b>\n\n"
            "بۆ ئەوەی وێبسایتەکەت بە تەواوی و بە کوالیتی بەرز دروست بکەم، پێویستە ئەم هەنگاوانە جێبەجێ بکەین:\n\n"
            "1️⃣ <b>دیزاین (Design & Concept):</b> تکایە سەرەتا **وێنەی دیزاینەکە** (Screenshot یان Witeframe) بنێرە یاخود شێوازی پێکهاتەکەی بە ڕستە کۆپی بکە و بۆم بنێرە.\n"
            "2️⃣ <b>هەڵبژاردنی زمان (Language):</b> دوای ناردنی دیزاینەکە، پێم بڵێ دەتەوێت بە چ زمانێک (بۆ نموونە HTML/CSS/JS یان PHP یان Framework) بۆت دروست بکەم.\n\n"
            "📌 <i>فەرموو سەرەتا وێنە یان شێوازی دیزاینی وێبەکەت بنێرە!</i>"
            + get_signature()
        )
        bot.reply_to(message, web_flow_msg)
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە", "کۆد بۆ", "کۆدێک بۆ"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>بیرکردنەوە...</b> (خەریکی شیکردنەوەی داواکارییەکەت و ئامادەکردنی کۆد/زانیاری)")
        
        web_results = perform_web_search(query)
        if web_results:
            response_content = web_results
        else:
            response_content = f"بابەتی ({query}) بە وردی لە ڕوانگەی پڕۆگرامسازی و تەکنەلۆجییەوە شیکرایەوە."

        response_text = (
            f"💻 <b>Programming & Tech Analysis:</b>\n\n"
            f"<b>داواکاری:</b> <i>{query}</i>\n\n"
            f"{response_content}"
            + get_signature()
        )
        
        try:
            bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=thinking_msg.message_id, parse_mode='HTML')
        except Exception:
            bot.send_message(message.chat.id, response_text, parse_mode='HTML')
        return

    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> گیانەکەم، تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد." + get_signature())
        return

    # دروستکردنی توڵ یان کۆدی پڕۆگرامسازی گشتی لەگەڵ داتابەیسی 10K
    rand_core = random.randint(5000, 9999)
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
    bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})" + get_signature())

if __name__ == '__main__':
    logger.info("Black Hat Universal Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
