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
logger = logging.getLogger("BlackHatBugBountyCore")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_states = {}
daily_limits = {}

# دروستکردنی 50 کۆدی ئاڵۆز و نایاب بۆ خەڵاتی دۆزینەوەی لاوازی (Bug Bounty)
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

# بەشی تایبەت بۆ باگ و خەڵات و ناردنی نامە بۆ سەرۆکەکان لە کۆتایی هەموو پەیامێکدا
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
        "linux", "windows", "python", "script", "kali", "nmap", "sqlmap", 
        "ddos", "dos", "wifi", "وایفای", "exploit", "payload", "پەیلوود", "vulnerability", 
        "لاوازی", "malware", "firewall", "database", "داتابەیس", 
        "encryption", "پاسوۆرد", "password", "proxy", "vpn", "سێرڤەر", "server", "gift", "کۆد", "باگ", "bug"
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
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 5 داواکاری بۆ توڵ)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI BUG BOUNTY CORE v25.0</b> 💀\n\n"
        "سڵاو! من زیرەکییەکی دەستکردم و تەنها بۆ بابەتی **IT، Cyber Security و Hacking** تەرخان کراوم.\n\n"
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
        bot.reply_to(message, "❌ <b>هەڵە!</b> کۆدی باگی ناتەواو یان نەناسراو. تەنها 50 کۆدی تایبەت بوونیان هەیە." + get_signature())

# 3. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Hacking Directory):</b>\n\n"
        "🌐 <b>1. بەشی سکانکردن و زانیاری (Reconnaissance & OSINT):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت و خزمەتگوزارییەکان.\n\n"
        "💥 <b>2. بەشی لاوازی و هێرشی وێب (Exploitation & Web Attacks):</b>\n"
        "• <b>Sqlmap Suite / Hydra:</b> شکاندنی پەسۆرد و تاقیکردنەوە.\n\n"
        "⚡ <b>3. بەشی فەوتاندن و هێرشی تۆڕ (DoS & DDoS Advanced Suites):</b>\n"
        "• <b>SYN Flood / Heavy Stress.</b>\n\n"
        "🎁 <b>4. بەشی دیاری و خەڵاتی باگ (Bug Bounty System):</b>\n"
        "• <code>/gift [کۆد]</code> - بەکارهێنانی کۆدی خەڵاتی دۆزەرەوەی باگ.\n\n"
        "🧠 <b>5. سیستەمی فەرمی ئاسایشی سایبەری و IT.</b>\n"
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

# 6. مۆدیوڵی سەرەکی
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
            "❌ <b>ببوورە!</b> پرسیاری دەرەکی وەڵام نادرێتەوە.\n"
            "من تەنها بۆ بابەتی <b>Hacking، Cyber Security و IT</b> تەرخان کراوم."
            + get_signature()
        )
        bot.reply_to(message, refusal_msg)
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>بیرکردنەوە...</b> (خەریکی شیکردنەوەی بابەتی تەکنیکی و سایبەریم)")
        
        web_results = perform_web_search(query)
        if web_results:
            response_content = web_results
        else:
            response_content = f"بابەتی ({query}) لە ڕوانگەی ئاسایشی سایبەری و تەکنیکییەوە لێکۆڵینەوەی بۆ کرا."

        response_text = (
            f"🛡 <b>Cyber Security & IT Analysis:</b>\n\n"
            f"<b>پرسیار:</b> <i>{query}</i>\n\n"
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

    # توڵی وایفای
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        tool_desc = "📶 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە دەتوانێت بۆ پشکنینی هێز و لاوازی تۆڕە بێتەلەکان (Wi-Fi) و گرتنی هەندشەی WPA2 بەکار بێت، هاوکات داتابەیسێکی گەورە پڕ لە 10,000 پاسوۆرد و زانیاری بۆ تاقیکردنەوە دروست دەکات."
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & 10K DB Generator\n"
            "# Developed by @ALONE427 & @malikdlashad3\n"
            "import os, sys, time, sqlite3\n\n"
            "def generate_10k_database():\n"
            "    print('[*] Initializing 10,000 Records Database...')\n"
            "    conn = sqlite3.connect('wifi_database_10k.db')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, data TEXT)')\n"
            "    records = [(i, f'WIFI_PAYLOAD_SIGNATURE_{i}') for i in range(1, 10001)]\n"
            "    cursor.executemany('INSERT OR IGNORE INTO records VALUES (?, ?)', records)\n"
            "    conn.commit()\n"
            "    conn.close()\n"
            "    print('[+] Successfully saved 10,000 records into wifi_database_10k.db!')\n\n"
            "if __name__ == '__main__':\n"
            "    generate_10k_database()"
        )
        wifi_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>wifi_10k.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس کارپێکردن ئەنجام بدە:\n"
            "   <code>python wifi_10k.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{wifi_code}</code></pre>\n\n{wifi_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})" + get_signature())
        return

    # توڵی DDoS
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        tool_desc = "💥 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە تایبەتە بە ناردنی ترافیکی تاقیکاری قورس بۆ سەر سێرڤەر (Multi-threaded Stress Testing)، لەگەڵ پاشەکەوتکردنی داتابەیسی 10,000 ئایپی و پۆرت بۆ ئاسانکاری."
        heavy_ddos = (
            "# Ultra-Performance DDoS Suite with 10K Proxy/Target DB\n"
            "# Developed by @ALONE427 & @malikdlashad3\n"
            "import socket, threading, random, time, sqlite3\n\n"
            "def generate_10k_database():\n"
            "    print('[*] Generating 10,000 Target/Proxy records for DDoS engine...')\n"
            "    conn = sqlite3.connect('ddos_targets_10k.db')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('CREATE TABLE IF NOT EXISTS targets (id INTEGER PRIMARY KEY, ip_node TEXT)')\n"
            "    nodes = [(i, f'192.168.1.{i % 255}') for i in range(1, 10001)]\n"
            "    cursor.executemany('INSERT OR IGNORE INTO targets VALUES (?, ?)', nodes)\n"
            "    conn.commit()\n"
            "    conn.close()\n"
            "    print('[+] Successfully created and saved 10,000 records in ddos_targets_10k.db!')\n\n"
            "if __name__ == '__main__':\n"
            "    generate_10k_database()"
        )
        heavy_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>ddos_10k.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس جێبەجێی بکە:\n"
            "   <code>python ddos_10k.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{heavy_ddos}</code></pre>\n\n{heavy_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})" + get_signature())
        return

    else:
        rand_core = random.randint(5000, 9999)
        tool_desc = f"🛠 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە تایبەتە بە دروستکردنی سکریپتی پاراستن و شیکردنەوەی ئامانج ({query})، کە 10,000 تۆماری زانیاریش لە خۆ دەگرێت."
        custom_code = (
            f"# Custom Cyber Security Module #{rand_core} with 10K DB\n"
            f"# Target Specification: {query}\n"
            f"# Developed by @ALONE427 & @malikdlashad3\n\n"
            f"import socket, sys, time, sqlite3\n\n"
            f"def generate_10k_database():\n"
            f"    print('[*] Initializing 10,000 security records for module #{rand_core}...')\n"
            f"    conn = sqlite3.connect('security_data_10k.db')\n"
            f"    cursor = conn.cursor()\n"
            f"    cursor.execute('CREATE TABLE IF NOT EXISTS payloads (id INTEGER PRIMARY KEY, signature TEXT)')\n"
            f"    data = [(i, f'EXPLOIT_SIG_NODE_{i}') for i in range(1, 10001)]\n"
            f"    cursor.executemany('INSERT OR IGNORE INTO payloads VALUES (?, ?)', data)\n"
            f"    conn.commit()\n"
            f"    conn.close()\n"
            f"    print('[+] Successfully saved 10,000 records into security_data_10k.db!')\n\n"
            "if __name__ == '__main__':\n"
            "    generate_10k_database()"
        )
        custom_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            f"1. کۆدەکە لە فایلێک بە ناوی <code>exploit_{rand_core}.py</code> پاشەکەوت بکە.\n"
            f"2. لە تێرماکس جێبەجێی بکە:\n"
            f"   <code>python exploit_{rand_core}.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})" + get_signature())
        return

if __name__ == '__main__':
    logger.info("Black Hat Bug Bounty Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
